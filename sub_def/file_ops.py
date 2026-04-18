# file_ops.py

from pathlib import Path
import os
import sys
import datetime
import pandas as pd
import pickle
from typing import Dict, List, Any
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


def log(msg):
    print(msg, file=sys.stderr)


# ===========#
# BBS関係    #
# ===========#
def ensure_logfile() -> None:
    """ログファイルの存在を保証"""
    if not LOGFILE.exists():
        LOGFILE.parent.mkdir(parents=True, exist_ok=True)
        LOGFILE.write_text("", encoding="utf-8")


def read_log() -> str:
    """ログを読み込み、逆順（最新を先頭）にして返す"""
    try:
        ensure_logfile()
        lines = LOGFILE.read_text(encoding="utf-8").splitlines(keepends=True)
        return "".join(reversed(lines))
    except (FileNotFoundError, IOError):
        return ""


def append_log(newlog: str) -> None:
    """ログを末尾に追記し、最大行数を制限"""
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
def _handle_file_error(operation: str, file_path: str, e: Exception) -> None:
    """ファイル操作時の例外を共通メッセージで処理"""
    if isinstance(e, FileNotFoundError):
        error(f"{operation}ファイルが見つかりません: {file_path}", 99)
    elif isinstance(e, (pickle.UnpicklingError, pd.errors.EmptyDataError)):
        error(f"{operation}ファイルの読み込みに失敗しました: {file_path}", 99)
    else:
        error(f"{operation}中にエラーが発生しました: {e}", 99)


def _ensure_lock_dirs() -> None:
    """ロック用ディレクトリ(user/shared)の存在を保証"""
    os.makedirs(os.path.join(Conf["savedir"], "locks", "user"), exist_ok=True)
    os.makedirs(os.path.join(Conf["savedir"], "locks", "shared"), exist_ok=True)


def get_user_lock(user: str):
    """ユーザー個別データ用ロックを返す（同一ユーザー更新の競合防止）"""
    _ensure_lock_dirs()
    lock_dir = os.path.join(Conf["savedir"], "locks", "user", user)
    return exLock.exLock(
        lock_dir,
        stale_seconds=120,
        retry_count=60,
        retry_interval=1.0,
    )


def get_shared_lock(name: str):
    """共有ファイル用ロックを返す（user_list など共通資産向け）"""
    _ensure_lock_dirs()
    lock_dir = os.path.join(Conf["savedir"], "locks", "shared", name)
    return exLock.exLock(
        lock_dir,
        stale_seconds=120,
        retry_count=60,
        retry_interval=1.0,
    )


def _atomic_text_save_unlocked(text: str, file_path: str) -> None:
    """テキストを一時ファイル経由で原子的に保存（lock取得は呼び出し側で行う）"""
    dir_path = os.path.dirname(file_path)
    os.makedirs(dir_path, exist_ok=True)

    temp_file_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            delete=False,
            dir=dir_path,
            prefix=".tmp_",
            suffix=".txt",
            encoding="utf-8",
        ) as temp_file:
            temp_file.write(text)
            temp_file.flush()
            os.fsync(temp_file.fileno())
            temp_file_path = temp_file.name

        os.replace(temp_file_path, file_path)

    except Exception as e:
        try:
            if temp_file_path and os.path.exists(temp_file_path):
                os.remove(temp_file_path)
        except Exception:
            pass
        _handle_file_error("text", file_path, e)


def _atomic_pickle_save_unlocked(data: Any, file_path: str) -> None:
    """pickleを一時ファイル経由で原子的に保存（lock取得は呼び出し側で行う）"""
    dir_path = os.path.dirname(file_path)
    os.makedirs(dir_path, exist_ok=True)

    temp_file_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            delete=False,
            dir=dir_path,
            prefix=".tmp_",
            suffix=".pickle",
        ) as temp_file:
            pickle.dump(data, temp_file, protocol=pickle.HIGHEST_PROTOCOL)
            temp_file.flush()
            os.fsync(temp_file.fileno())
            temp_file_path = temp_file.name

        os.replace(temp_file_path, file_path)

    except Exception as e:
        try:
            if temp_file_path and os.path.exists(temp_file_path):
                os.remove(temp_file_path)
        except Exception:
            pass
        _handle_file_error("pickle", file_path, e)


def get_file_path(file: str, user: str = "") -> str:
    """
    ファイルのパスを取得
    - .pickle が付いている → pickle用パス
    - .csv が付いている → CSV用パス
    """
    # 拡張子を取り除いてベースとなるキー名を取得 ("user_list.csv" -> "user_list")
    base_name = file.replace(".pickle", "").replace(".csv", "")
    is_pickle = file.endswith(".pickle")

    # MASTER
    if base_name in CSV_DEFS_MASTER:
        if is_pickle:
            return os.path.join(Conf["datdir"], PICKLE_DIR, file)
        return os.path.join(Conf["datdir"], file)

    # GLOBAL
    elif base_name in CSV_DEFS_GLOBAL:
        return os.path.join(Conf["savedir"], file)

    # USER
    elif base_name in CSV_DEFS_USER or base_name == "user_all":
        if not user:
            error(f"ユーザー名必須: {file}", "top")
        if is_pickle:
            return os.path.join(Conf["savedir"], user, PICKLE_DIR, file)
        return os.path.join(Conf["savedir"], user, file)

    # fallback
    else:
        error(f"未定義ファイル: {file}", "top")


def _create_pickle_accessor(file_name: str):
    """open_xxx / save_xxx 用の簡易アクセサを生成"""
    file_name = f"{file_name}.pickle"

    def load(user: str = ""):
        return pickle_load(file_name, user)

    def dump(data: Any, user: str = ""):
        pickle_dump(data, file_name, user)

    return load, dump


def _create_global_pickle_accessor(file_name: str):
    """グローバルlist系open_xxx / save_xxx 用の簡易アクセサを生成"""
    file_name = f"{file_name}.pickle"

    def load():
        return _load_pickle_list(file_name)

    def dump(data: Dict):
        _save_pickle_list(data, file_name)

    return load, dump


# ======================#
# pickle(ユーザー系)操作 #
# ======================#
def pickle_load(file: str, user: str = "") -> Any:
    """ユーザー個別pickleのフルパスを返す。user未指定時はsessionのin_nameを参照"""
    if user == "":
        s = get_session()
        user = s.get("in_name") or ""

    file_path = get_file_path(file, user)

    try:
        with open(file_path, mode="rb") as f:
            return pickle.load(f)
    except FileNotFoundError:
        error(f"pickleファイルが見つかりません: {file_path}", 99)
    except pickle.UnpicklingError:
        error(f"pickleファイルの読み込みに失敗しました: {file_path}", 99)
    except Exception as e:
        error(f"pickleファイルの読み込み中にエラーが発生しました: {e}", 99)


def pickle_dump(data: Any, file: str, user: str = "") -> None:
    s = get_session()
    user = user or s.get("in_name") or ""

    file_path = get_file_path(file, user)

    # 拡張子を取り除いてベースとなるキー名を取得
    base_name = file.replace(".pickle", "").replace(".csv", "")

    if base_name in CSV_DEFS_GLOBAL:
        lock = get_shared_lock(file)
    else:
        lock = get_user_lock(user)

    if not lock.lock():
        error("現在サーバーが込み合っています。", "top")

    try:
        _atomic_pickle_save_unlocked(data, file_path)
    finally:
        lock.unlock()


# =============================#
# pickle(グローバルリスト系)操作 #
# =============================#
def initialize_pickle(file_name: str, initial_data: Any = None) -> None:
    """共有pickleを初期データ付きで新規作成"""
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
    """共有pickle(dict前提)を読み込む。無ければ初期化する"""

    file_path = get_file_path(file)

    if not os.path.exists(file_path):
        initialize_pickle(file)

    try:
        with open(file_path, mode="rb") as f:
            return pickle.load(f)
    except Exception as e:
        error(f"{file}の読み込み中にエラーが発生しました: {e}", 99)
        return {}


def _save_pickle_list(data: Dict, file: str) -> None:
    """共有pickle(dict前提)を書き込む"""
    file_path = get_file_path(file)

    lock = get_shared_lock(file)
    if not lock.lock():
        error("現在サーバーが込み合っています。", "top")

    try:
        _atomic_pickle_save_unlocked(data, file_path)
    finally:
        lock.unlock()


def get_ranked_user_list(user_list: dict):
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
    """dat/pickle配下の共通マスタを読み込む"""
    # 共通の get_file_path を通すように修正
    file_path = get_file_path(f"{file_name}.pickle")

    try:
        with open(file_path, "rb") as f:
            return pickle.load(f)
    except Exception as e:
        _handle_file_error("dat", file_path, e)
        return {}


def _create_dat_opener(file_name: str):
    """open_xxx_dat 用の簡易アクセサを生成"""
    return lambda: open_dat(file_name)


# ======================#
# 完全移行用：ユーザー全データ1ファイル
# ======================#
def open_user_all(user: str = "") -> dict:
    """ユーザー個別全データを1ファイルで読み込み（安全版）"""
    if not user:
        error("open_user_all: ユーザー名が指定されていません", "top")

    file_name = "user_all.pickle"
    file_path = get_file_path(file_name, user)

    try:
        with open(file_path, mode="rb") as f:
            data = pickle.load(f)

        # 後方互換性
        default = {
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

    except FileNotFoundError:
        # まだ user_all.pickle が存在しない場合のみ、従来方式で合成
        try:
            return {
                "user": open_user(user),  # ここは従来のまま（一時的）
                "party": open_party(user),
                "vips": open_vips(user),
                "room_key": open_room_key(user),
                "waza": open_waza(user),
                "park": open_park(user),
                "zukan": open_zukan(user),
            }
        except Exception as e:
            print(f"フォールバック失敗 ({user}): {e}", file=sys.stderr)
            return {
                "user": {},
                "party": [],
                "vips": {},
                "room_key": {},
                "waza": {},
                "park": [],
                "zukan": {},
            }

    except Exception as e:
        _handle_file_error("user_all", file_path, e)
        return {
            "user": {},
            "party": [],
            "vips": {},
            "room_key": {},
            "waza": {},
            "park": [],
            "zukan": {},
        }


def save_user_all(data: dict, user: str = "") -> None:
    """1ファイルにまとめて保存（安全版）"""
    if not user:
        error("save_user_all: ユーザー名が指定されていません", "top")

    file_name = "user_all.pickle"
    file_path = get_file_path(file_name, user)

    data = dict(data)  # コピー
    data["updated_at"] = datetime.datetime.now().isoformat()

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
    """トーナメント開催日文字列の保存/読込を管理"""

    FILE_PATH = os.path.join(Conf["savedir"], "tournament_time.txt")
    FORMAT = "%Y年%m月%d日"
    LOCK_NAME = "tournament_time"

    @staticmethod
    def calculate_next_date(today: datetime.date = None) -> str:
        """次回開催日(1日/11日/21日区切り)を文字列で返す"""
        today = today or datetime.date.today()
        day = today.day

        if 1 <= day < 11:
            next_day = 11
            base_date = today
        elif 11 <= day < 21:
            next_day = 21
            base_date = today
        else:
            next_day = 1
            next_month = today.month % 12 + 1
            next_year = today.year + (today.month // 12)
            base_date = today.replace(year=next_year, month=next_month)

        next_date = base_date.replace(day=next_day)
        return next_date.strftime(TournamentScheduler.FORMAT)

    @staticmethod
    def save_date(date_str: str) -> None:
        """開催日を共有ロック付きで保存し、状態キャッシュを破棄する"""
        lock = get_shared_lock(TournamentScheduler.LOCK_NAME)
        if not lock.lock():
            error("現在サーバーが込み合っています。", "top")

        try:
            _atomic_text_save_unlocked(date_str, TournamentScheduler.FILE_PATH)
        finally:
            lock.unlock()

    @staticmethod
    def load_date() -> str:
        """開催日を読み込む。無効/未作成時は再計算して保存する"""
        if not os.path.exists(TournamentScheduler.FILE_PATH):
            date_str = TournamentScheduler.calculate_next_date()
            TournamentScheduler.save_date(date_str)
            return date_str

        try:
            with open(TournamentScheduler.FILE_PATH, encoding="utf-8") as f:
                date_str = f.read().strip()

            datetime.datetime.strptime(date_str, TournamentScheduler.FORMAT)
            return date_str

        except (ValueError, OSError):
            date_str = TournamentScheduler.calculate_next_date()
            TournamentScheduler.save_date(date_str)
            return date_str


def timesyori() -> str:
    """次のトーナメント日付を計算して保存"""
    date_str = TournamentScheduler.calculate_next_date()
    TournamentScheduler.save_date(date_str)
    return date_str


def open_tournament_time() -> str:
    """トーナメント日付を読み込み"""
    return TournamentScheduler.load_date()


def get_tournament_status() -> Dict:
    """トーナメント日時と残日数を返す"""
    t_time = open_tournament_time()
    try:
        t_date = datetime.datetime.strptime(t_time, TournamentScheduler.FORMAT)
        t_count = (t_date - datetime.datetime.now()).days
        return {"t_time": t_time, "t_count": t_count}
    except ValueError:
        timesyori()
        return {"t_time": open_tournament_time(), "t_count": 0}


# ===============#
# list系         #
# ===============#
open_user_list, save_user_list = _create_global_pickle_accessor("user_list")
open_omiai_list, save_omiai_list = _create_global_pickle_accessor("omiai_list")

# ===============#
# user個別pickle #
# ===============#
open_user, save_user = _create_pickle_accessor("user")
open_party, save_party = _create_pickle_accessor("party")
open_vips, save_vips = _create_pickle_accessor("vips")
open_zukan, save_zukan = _create_pickle_accessor("zukan")
open_waza, save_waza = _create_pickle_accessor("waza")
open_room_key, save_room_key = _create_pickle_accessor("room_key")
open_battle, save_battle = _create_pickle_accessor("battle")
open_park, save_park = _create_pickle_accessor("park")

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
