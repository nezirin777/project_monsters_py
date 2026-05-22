# file_ops.py

from pathlib import Path
import os
import sys
import datetime
import pandas as pd
import pickle
from typing import Callable, Dict, List, Any, NoReturn, Tuple
import tempfile
import conf
import exLock

from .utils import error
from .crypto import get_session

Conf = conf.Conf

PICKLE_DIR = "./pickle"

# ログ設定
LOGFILE = Path(Conf["savedir"]) / "bbslog.log"
MAX_LOG_LINES = Conf["max_log_lines"]

# ログファイルは共有資産なので共有ロックを使う
LOG_LOCK = exLock.exLock(
    os.path.join(Conf["savedir"], "locks", "shared", "log"),
    stale_seconds=120,
    retry_count=5,
    retry_interval=1.0,
)

# CSVごとの主キー列
CSV_DEFS_MASTER = Conf.get("csv_defs_master", {})
CSV_DEFS_GLOBAL = Conf.get("csv_defs_global", {})
CSV_DEFS_USER = Conf.get("csv_defs_user", {})


def log(msg: str) -> None:
    """デバッグ・実行ログを標準エラー出力に流す"""
    print(msg, file=sys.stderr)


# ===========#
# BBS関係    #
# ===========#
def ensure_logfile() -> None:
    """ログファイルの存在を保証する。なければ空ファイルを作成する"""
    if not LOGFILE.exists():
        LOGFILE.parent.mkdir(parents=True, exist_ok=True)
        LOGFILE.write_text("", encoding="utf-8")


def read_log() -> str:
    """ログを読み込み、最新を先頭にして返す"""
    try:
        ensure_logfile()
        lines = LOGFILE.read_text(encoding="utf-8").splitlines(keepends=True)
        return "".join(reversed(lines))
    except (FileNotFoundError, IOError):
        return ""


def append_log(newlog: str) -> None:
    """ログを末尾に追記し、最大行数を超えた分を先頭から切り捨てる"""
    if not LOG_LOCK.lock():
        error("現在サーバーが込み合っています。", "top")

    try:
        ensure_logfile()
        lines = LOGFILE.read_text(encoding="utf-8").splitlines()
        new_lines = newlog.splitlines()
        lines.extend(new_lines)

        if len(lines) > MAX_LOG_LINES:
            lines = lines[-MAX_LOG_LINES:]

        LOGFILE.write_text("".join(line + "\n" for line in lines), encoding="utf-8")

    except IOError as e:
        error(f"ログ操作に失敗しました: {e}")
    finally:
        LOG_LOCK.unlock()


# ==========================#
# 内部ヘルパー / 共通処理   #
# ==========================#
def _handle_file_error(operation: str, file_path: str, e: Exception) -> NoReturn:
    """
    ファイル操作時の例外を種別に応じたメッセージで処理する。
    error() → sys.exit() を必ず呼ぶため NoReturn。
    """
    if isinstance(e, FileNotFoundError):
        error(f"{operation}ファイルが見つかりません: {file_path}", 99)
    elif isinstance(e, (pickle.UnpicklingError, pd.errors.EmptyDataError)):
        error(f"{operation}ファイルの読み込みに失敗しました: {file_path}", 99)
    else:
        error(f"{operation}中にエラーが発生しました: {e}", 99)

    # error() が sys.exit() を呼ぶため到達しないが、
    # NoReturn 宣言に対する型チェッカーの警告を抑制するために記述する
    raise RuntimeError("unreachable")


def _ensure_lock_dirs() -> None:
    """ロック用ディレクトリ (user / shared) の存在を保証する"""
    os.makedirs(os.path.join(Conf["savedir"], "locks", "user"), exist_ok=True)
    os.makedirs(os.path.join(Conf["savedir"], "locks", "shared"), exist_ok=True)


def get_user_lock(user: str) -> exLock.exLock:
    """ユーザー個別データ用ロックを返す（同一ユーザーへの並列書き込みを防ぐ）"""
    _ensure_lock_dirs()
    lock_dir = os.path.join(Conf["savedir"], "locks", "user", user)
    return exLock.exLock(
        lock_dir,
        stale_seconds=120,
        retry_count=60,
        retry_interval=1.0,
    )


def get_shared_lock(name: str) -> exLock.exLock:
    """共有ファイル用ロックを返す（user_list など複数リクエストが触れる資産向け）"""
    _ensure_lock_dirs()
    lock_dir = os.path.join(Conf["savedir"], "locks", "shared", name)
    return exLock.exLock(
        lock_dir,
        stale_seconds=120,
        retry_count=60,
        retry_interval=1.0,
    )


# ====================================================#
# アトミック保存 共通実装                              #
# ====================================================#
def _atomic_save_unlocked(
    file_path: str,
    write_fn: Callable[[Any], None],
    open_kwargs: dict,
    error_label: str,
) -> None:
    """
    一時ファイルを経由したアトミック保存の共通実装。
    書き込み完了後に os.replace() で置き換えることでファイル破損を防ぐ。
    呼び出し側でロックを取得してから使うこと（この関数自体はロックを取得しない）。

    Args:
        file_path  : 最終的な保存先パス
        write_fn   : ファイルオブジェクトを受け取り書き込みを行う関数
        open_kwargs: NamedTemporaryFile に渡す追加キーワード引数 (mode, suffix, encoding 等)
        error_label: エラー発生時のメッセージ用ラベル
    """
    dir_path = os.path.dirname(file_path)
    os.makedirs(dir_path, exist_ok=True)

    temp_file_path = None
    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            dir=dir_path,
            prefix=".tmp_",
            **open_kwargs,
        ) as temp_file:
            write_fn(temp_file)
            temp_file.flush()
            os.fsync(temp_file.fileno())
            temp_file_path = temp_file.name

        os.replace(temp_file_path, file_path)

    except Exception as e:
        # 失敗時は一時ファイルを確実に削除する
        try:
            if temp_file_path and os.path.exists(temp_file_path):
                os.remove(temp_file_path)
        except Exception:
            pass
        _handle_file_error(error_label, file_path, e)


def _atomic_text_save_unlocked(text: str, file_path: str) -> None:
    """テキストを一時ファイル経由でアトミックに保存する"""
    _atomic_save_unlocked(
        file_path=file_path,
        write_fn=lambda f: f.write(text),
        open_kwargs={"mode": "w", "suffix": ".txt", "encoding": "utf-8"},
        error_label="text",
    )


def _atomic_pickle_save_unlocked(data: Any, file_path: str) -> None:
    """pickle を一時ファイル経由でアトミックに保存する"""
    _atomic_save_unlocked(
        file_path=file_path,
        write_fn=lambda f: pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL),
        open_kwargs={"mode": "wb", "suffix": ".pickle"},
        error_label="pickle",
    )


# ====================================================#
# ファイルパス解決                                     #
# ====================================================#
def get_file_path(file: str, user: str = "") -> str:
    """
    ファイル名とユーザー名からフルパスを解決して返す。

    分類:
        MASTER  : dat/ 配下のマスタデータ（モンスター定義等）
        GLOBAL  : save/ 直下の全ユーザー共有データ（user_list 等）
        USER    : save/<user>/ 配下のユーザー個別データ
    """
    # 拡張子を除いたベースキーで分類を判定する
    base_name = file.replace(".pickle", "").replace(".csv", "")
    is_pickle = file.endswith(".pickle")

    if base_name in CSV_DEFS_MASTER:
        if is_pickle:
            return os.path.join(Conf["datdir"], PICKLE_DIR, file)
        return os.path.join(Conf["datdir"], file)

    elif base_name in CSV_DEFS_GLOBAL:
        return os.path.join(Conf["savedir"], file)

    elif base_name in CSV_DEFS_USER or base_name in ("user_all", "battle"):
        if not user:
            error(f"ユーザー名必須: {file}", "top")
        if is_pickle:
            return os.path.join(Conf["savedir"], user, PICKLE_DIR, file)
        return os.path.join(Conf["savedir"], user, file)

    else:
        error(f"未定義ファイル: {file}", "top")

    # error() → sys.exit() で到達しないが、型チェッカー向けに明示する
    raise RuntimeError("unreachable")


# =============================#
# pickle(グローバルリスト系)操作 #
# =============================#
def initialize_pickle(file_name: str, initial_data: Any = None) -> None:
    """共有 pickle を初期データ付きで新規作成する"""
    if initial_data is None:
        initial_data = {}

    file_path = get_file_path(file_name)

    lock = get_shared_lock(file_name)
    if not lock.lock():
        error("現在サーバーが込み合っています。", "top")

    try:
        _atomic_pickle_save_unlocked(initial_data, file_path)
    finally:
        lock.unlock()


def _load_pickle_list(file: str) -> Dict:
    """共有 pickle（dict 前提）を読み込む。存在しない場合は空辞書で初期化する"""
    file_path = get_file_path(file)

    if not os.path.exists(file_path):
        initialize_pickle(file)

    try:
        with open(file_path, mode="rb") as f:
            return pickle.load(f)
    except Exception as e:
        error(f"{file}の読み込み中にエラーが発生しました: {e}", 99)
        raise RuntimeError("unreachable")


def _save_pickle_list(data: Dict, file: str) -> None:
    """共有 pickle（dict 前提）を書き込む"""
    file_path = get_file_path(file)

    lock = get_shared_lock(file)
    if not lock.lock():
        error("現在サーバーが込み合っています。", "top")

    try:
        _atomic_pickle_save_unlocked(data, file_path)
    finally:
        lock.unlock()


def _create_global_pickle_accessor(file_name: str) -> Tuple[Callable, Callable]:
    """
    グローバルリスト系 (open_xxx / save_xxx) の関数ペアを生成して返す。

    使用例:
        open_user_list, save_user_list = _create_global_pickle_accessor("user_list")
    """
    full_name = f"{file_name}.pickle"

    def load() -> Dict:
        return _load_pickle_list(full_name)

    def dump(data: Dict) -> None:
        _save_pickle_list(data, full_name)

    return load, dump


def get_ranked_user_list(user_list: dict) -> dict:
    """ユーザーリストを key（最深部階層）の降順でソートし、rank を付与して返す"""
    sorted_items = sorted(
        user_list.items(),
        key=lambda x: x[1].get("key", 0),
        reverse=True,
    )

    new_dict = {}
    for i, (uid, data) in enumerate(sorted_items, start=1):
        d = data.copy()
        d["rank"] = i
        new_dict[uid] = d

    return new_dict


# ====================================#
# dat / 共通マスタ類読み込み          #
# ====================================#
def open_dat(file_name: str) -> Dict:
    """dat/pickle 配下の共通マスタデータを読み込む"""
    file_path = get_file_path(f"{file_name}.pickle")

    try:
        with open(file_path, "rb") as f:
            return pickle.load(f)
    except Exception as e:
        _handle_file_error("dat", file_path, e)

    # _handle_file_error が NoReturn のためここには到達しない
    # （mypy / Pyright 等の型チェッカー向けに記述）
    raise RuntimeError("unreachable")


def _create_dat_opener(file_name: str) -> Callable[[], Dict]:
    """
    open_xxx_dat 関数を生成して返す。

    ラムダの代わりに def を使うことで PEP 8 に準拠し、
    スタックトレースでも関数名が明示される。
    """

    def opener() -> Dict:
        return open_dat(file_name)

    # デバッグ時に識別しやすいよう __name__ を設定する
    opener.__name__ = f"open_{file_name}"
    return opener


# ======================#
# ユーザー全データ (1ファイル化)
# ======================#
def open_user_all(user: str = "") -> dict:
    """ユーザー個別の全データを 1 pickle ファイルから一括読み込みする"""
    if not user:
        s = get_session()
        user = s.get("in_name") or ""
        if not user:
            error("open_user_all: ユーザー名が指定されていません", "top")

    file_name = "user_all.pickle"
    file_path = get_file_path(file_name, user)

    try:
        with open(file_path, mode="rb") as f:
            data = pickle.load(f)

        # キーが欠損しているデータへの安全対策（古いセーブデータとの互換用）
        default: dict = {
            "user": {},
            "party": [],
            "vips": {},
            "room_key": {},
            "waza": {},
            "park": [],
            "zukan": {},
        }
        for key in default:
            if key not in data:
                data[key] = default[key]
        return data

    except Exception as e:
        _handle_file_error("user_all", file_path, e)

    raise RuntimeError("unreachable")


def save_user_all(data: dict, user: str = "") -> None:
    """ユーザー全データを 1 pickle ファイルに一括保存する"""
    if not user:
        s = get_session()
        user = s.get("in_name") or ""
        if not user:
            error("save_user_all: ユーザー名が指定されていません", "top")

    file_name = "user_all.pickle"
    file_path = get_file_path(file_name, user)

    data = dict(data)
    data["updated_at"] = datetime.datetime.now().isoformat()

    lock = get_user_lock(user)
    if not lock.lock():
        error("現在サーバーが込み合っています。", "top")

    try:
        _atomic_pickle_save_unlocked(data, file_path)
    finally:
        lock.unlock()


# ======================#
# バトル専用の一時ファイル
# ======================#
def open_battle(user: str = "") -> Any:
    """
    戦闘中の一時データを読み込む。
    ファイルが存在しない場合は None を返す（非戦闘時は正常系）。
    """
    if not user:
        s = get_session()
        user = s.get("in_name") or ""
        if not user:
            error("open_battle: ユーザー名が指定されていません", "top")

    file_path = get_file_path("battle.pickle", user)
    try:
        with open(file_path, mode="rb") as f:
            return pickle.load(f)
    except FileNotFoundError:
        return None
    except Exception as e:
        _handle_file_error("battle", file_path, e)

    raise RuntimeError("unreachable")


def save_battle(data: Any, user: str = "") -> None:
    """戦闘中の一時データを書き込む"""
    if not user:
        s = get_session()
        user = s.get("in_name") or ""
        if not user:
            error("save_battle: ユーザー名が指定されていません", "top")

    file_path = get_file_path("battle.pickle", user)

    lock = get_user_lock(user)
    if not lock.lock():
        error("現在サーバーが込み合っています。", "top")

    try:
        _atomic_pickle_save_unlocked(data, file_path)
    finally:
        lock.unlock()


# =========================#
# メダル杯開催時間ファイル #
# =========================#
class TournamentScheduler:
    """トーナメント開催日文字列の保存 / 読込を管理するユーティリティクラス"""

    FILE_PATH = os.path.join(Conf["savedir"], "tournament_time.txt")
    FORMAT = "%Y年%m月%d日"
    LOCK_NAME = "tournament_time"

    @staticmethod
    def calculate_next_date(today: datetime.date = None) -> str:
        """次回開催日（1日 / 11日 / 21日）を文字列で返す"""
        today = today or datetime.date.today()
        day = today.day

        if 1 <= day < 11:
            next_day = 11
            base_date = today
        elif 11 <= day < 21:
            next_day = 21
            base_date = today
        else:
            # 月末を超える場合は翌月1日に切り替える
            next_day = 1
            next_month = today.month % 12 + 1
            next_year = today.year + (today.month // 12)
            base_date = today.replace(year=next_year, month=next_month)

        next_date = base_date.replace(day=next_day)
        return next_date.strftime(TournamentScheduler.FORMAT)

    @staticmethod
    def save_date(date_str: str) -> None:
        """開催日を共有ロック付きで保存する"""
        lock = get_shared_lock(TournamentScheduler.LOCK_NAME)
        if not lock.lock():
            error("現在サーバーが込み合っています。", "top")

        try:
            _atomic_text_save_unlocked(date_str, TournamentScheduler.FILE_PATH)
        finally:
            lock.unlock()

    @staticmethod
    def load_date() -> str:
        """
        開催日文字列を読み込む。
        ファイルが存在しない・フォーマット不正の場合は再計算して保存する。
        """
        if not os.path.exists(TournamentScheduler.FILE_PATH):
            date_str = TournamentScheduler.calculate_next_date()
            TournamentScheduler.save_date(date_str)
            return date_str

        try:
            with open(TournamentScheduler.FILE_PATH, encoding="utf-8") as f:
                date_str = f.read().strip()

            # フォーマット検証（不正な場合は ValueError が発生して except へ）
            datetime.datetime.strptime(date_str, TournamentScheduler.FORMAT)
            return date_str

        except (ValueError, OSError):
            date_str = TournamentScheduler.calculate_next_date()
            TournamentScheduler.save_date(date_str)
            return date_str


def timesyori() -> str:
    """次のトーナメント日付を計算して保存し、その文字列を返す"""
    date_str = TournamentScheduler.calculate_next_date()
    TournamentScheduler.save_date(date_str)
    return date_str


def open_tournament_time() -> str:
    """トーナメント開催日文字列を読み込む"""
    return TournamentScheduler.load_date()


def get_tournament_status() -> Dict:
    """トーナメント開催日時と残日数を辞書で返す"""
    t_time = open_tournament_time()
    try:
        t_date = datetime.datetime.strptime(t_time, TournamentScheduler.FORMAT)
        t_count = (t_date - datetime.datetime.now()).days
        return {"t_time": t_time, "t_count": t_count}
    except ValueError:
        # フォーマット不正ならリセットして再取得する
        timesyori()
        return {"t_time": open_tournament_time(), "t_count": 0}


# ===============#
# list系         #
# ===============#
open_user_list, save_user_list = _create_global_pickle_accessor("user_list")
open_omiai_list, save_omiai_list = _create_global_pickle_accessor("omiai_list")


# ===============#
# dat系          #
# ===============#
open_book_dat = _create_dat_opener("book_dat")
open_key_dat = _create_dat_opener("key_dat")
open_seikaku_dat = _create_dat_opener("seikaku_dat")
open_tokugi_dat = _create_dat_opener("tokugi_dat")
open_medal_shop_dat = _create_dat_opener("medal_shop_dat")
open_monster_boss_dat = _create_dat_opener("monster_boss_dat")
open_monster_dat = _create_dat_opener("monster_dat")
open_vips_shop_dat = _create_dat_opener("vips_shop_dat")
open_vips_shop2_dat = _create_dat_opener("vips_shop2_dat")
open_vips_shop3_dat = _create_dat_opener("vips_shop3_dat")
