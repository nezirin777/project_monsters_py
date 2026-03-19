# file_ops.py

from pathlib import Path
import os
import datetime
import pandas as pd
import pickle
from typing import Dict, List, Any
from functools import lru_cache
import tempfile
import conf
import exLock

from .utils import error
from .crypto import get_session

Conf = conf.Conf

PICKLE_DIR = "pickle"

# ======================#
# ログ設定              #
# ======================#
LOGFILE = Path(Conf["savedir"]) / "bbslog.log"
MAX_LOG_LINES = Conf["max_log_lines"]

# ログファイルは共有資産なので共有ロックを使う
LOG_LOCK = exLock.exLock(
    os.path.join(Conf["savedir"], "locks", "shared", "log"),
    stale_seconds=120,
    retry_count=60,
    retry_interval=1.0,
)

# CSVごとの主キー列
CSV_INDEX_MAP = {
    "user_list.csv": "user_name",
    "omiai_list.csv": "user_name",
    "book_dat.csv": "name",
    "key_dat.csv": "name",
    "seikaku_dat.csv": "name",
    "tokugi_dat.csv": "name",
    "medal_shop_dat.csv": "name",
    "monster_boss_dat.csv": "name",
    "monster_dat.csv": "name",
    "vips_shop_dat.csv": "name",
    "vips_shop2_dat.csv": "name",
    "vips_shop3_dat.csv": "id",
    "battle.csv": "name",
    "park.csv": "name",
    "party.csv": "name",
    "room_key.csv": "name",
    "user.csv": "name",
    "vips.csv": "name",
    "waza.csv": "name",
    "zukan.csv": "name",
}

# 読み込み済みログキャッシュ
_log_cache = None


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
    global _log_cache
    if _log_cache is None:
        try:
            lines = LOGFILE.read_text(encoding="utf-8").splitlines()
            _log_cache = "".join(lines[::-1])
        except (FileNotFoundError, IOError):
            _log_cache = ""
    return _log_cache


def append_log(newlog: str) -> None:
    """ログを末尾に追記し、最大行数を制限"""
    global _log_cache

    if not LOG_LOCK.lock():
        error("現在サーバーが込み合っています。", "top")

    try:
        ensure_logfile()

        with LOGFILE.open("a", encoding="utf-8") as f:
            f.write(newlog)

        lines = (newlog + (_log_cache or "")).splitlines()
        if len(lines) > MAX_LOG_LINES:
            lines = lines[-MAX_LOG_LINES:]
        _log_cache = "".join(lines[::-1])

        with LOGFILE.open("w", encoding="utf-8") as f:
            f.writelines(line + "\n" for line in lines)

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


def get_file_path(file: str, user: str = "", dir_type: str = "savedir") -> str:
    """保存先/データ置き場の基本パスを組み立てる"""
    base_dir = Conf["savedir"] if dir_type == "savedir" else Conf["datdir"]
    if user and dir_type == "savedir":
        return os.path.join(base_dir, user, PICKLE_DIR, f"{file}.pickle")
    return os.path.join(base_dir, file)


def get_pickle_file_path(file: str, user: str = "") -> str:
    """ユーザー個別pickleのフルパスを返す。user未指定時はsessionのin_nameを参照"""
    s = get_session()
    name = user or s.get("in_name") or ""
    if not name:
        error(
            f"pickleファイル操作エラー: ユーザー名が存在していません。{file}/ユーザー名：{name}",
            99,
        )
    return get_file_path(file, name)


def pickle_load(file: str, user: str = "") -> Any:
    """ユーザー個別pickleを読み込む"""
    file_path = get_pickle_file_path(file, user)
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
    """ユーザー個別pickleを書き込む。userありならユーザー単位、なしなら共有ロックを使う"""
    file_path = get_pickle_file_path(file, user)

    lock = get_user_lock(user) if user else get_shared_lock(file)
    if not lock.lock():
        error("現在サーバーが込み合っています。", "top")

    try:
        _atomic_pickle_save_unlocked(data, file_path)
    finally:
        lock.unlock()


def _create_pickle_accessor(file_name: str):
    """open_xxx / save_xxx 用の簡易アクセサを生成"""

    def load(user: str = ""):
        return pickle_load(file_name, user)

    def dump(data: Any, user: str = ""):
        pickle_dump(data, file_name, user)

    return load, dump


def initialize_pickle(file_name: str, initial_data: Any = None) -> None:
    """共有pickleを初期データ付きで新規作成"""
    initial_data = initial_data or {}
    file_path = os.path.join(Conf["savedir"], file_name)

    lock = get_shared_lock(file_name)
    if not lock.lock():
        error("現在サーバーが込み合っています。", "top")

    try:
        _atomic_pickle_save_unlocked(initial_data, file_path)
    finally:
        lock.unlock()


def _load_pickle_list(file: str) -> Dict:
    """共有pickle(dict前提)を読み込む。無ければ初期化する"""
    file_path = os.path.join(Conf["savedir"], f"{file}.pickle")
    if not os.path.exists(file_path):
        initialize_pickle(f"{file}.pickle")

    try:
        with open(file_path, mode="rb") as f:
            return pickle.load(f)
    except Exception as e:
        error(f"{file}の読み込み中にエラーが発生しました: {e}", 99)
        return {}


def _save_pickle_list(data: Dict, file: str) -> None:
    """共有pickle(dict前提)を書き込む"""
    file_path = os.path.join(Conf["savedir"], f"{file}.pickle")

    lock = get_shared_lock(file)
    if not lock.lock():
        error("現在サーバーが込み合っています。", "top")

    try:
        _atomic_pickle_save_unlocked(data, file_path)
    finally:
        lock.unlock()


# ===============#
# CSV操作        #
# ===============#
def get_csv_file_path(file: str, name: str = "") -> str:
    """CSVファイルのフルパスを返す"""
    return get_file_path(file, name) if name else get_file_path(file)


def open_csv_dict(file: str, name: str = "") -> Dict:
    """CSVをindex付きdictとして読み込む"""
    file_path = get_csv_file_path(file, name)
    index_col = CSV_INDEX_MAP.get(file, "name")
    sort_val = file not in ["user_list.csv", "omiai_list.csv"]

    try:
        df = pd.read_csv(
            file_path,
            encoding="utf-8_sig",
            index_col=index_col,
            na_filter=False,
        ).convert_dtypes()

        if sort_val and "no" in df.columns:
            df = df.sort_values("no")

        return df.to_dict(orient="index")

    except Exception as e:
        _handle_file_error("CSV", file_path, e)
        return {}


def open_csv_list(file: str, name: str = "", single: bool = False) -> List | Dict:
    """CSVをレコード配列として読み込む。single=Trueなら先頭1件のみ返す"""
    file_path = get_csv_file_path(file, name)
    try:
        df = (
            pd.read_csv(file_path, encoding="utf-8_sig", na_filter=False)
            .dropna(how="all")
            .convert_dtypes()
        )
    except Exception as e:
        _handle_file_error("CSV", file_path, e)
        return [{}] if single else []

    if df.empty:
        return [{}] if single else []

    string_cols = [col for col in df.columns if pd.api.types.is_string_dtype(df[col])]
    nullable_cols = [
        col for col in df.columns if df[col].isnull().any() and col not in string_cols
    ]

    if string_cols:
        df[string_cols] = df[string_cols].fillna("")

    if nullable_cols:
        df[nullable_cols] = df[nullable_cols].where(df[nullable_cols].notna(), None)

    records = df.to_dict(orient="records")
    return records[0] if single else records


# ====================================#
# dat / 共通マスタ類読み込み          #
# ====================================#
@lru_cache(maxsize=128)
def open_dat(file_name: str) -> Dict:
    """dat/pickle配下の共通マスタを読み込む（キャッシュあり）"""
    file_path = os.path.join(Conf["datdir"], "pickle", f"{file_name}.pickle")
    try:
        with open(file_path, "rb") as f:
            return pickle.load(f)
    except Exception as e:
        _handle_file_error("dat", file_path, e)
        return {}


def _create_dat_opener(file_name: str):
    """open_xxx_dat 用の簡易アクセサを生成"""
    return lambda: open_dat(file_name)


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
            get_tournament_status.cache_clear()
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


@lru_cache(maxsize=1)
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
def open_user_list() -> Dict:
    return _load_pickle_list("user_list")


def save_user_list(data: Dict) -> None:
    _save_pickle_list(data, "user_list")


def open_omiai_list() -> Dict:
    return _load_pickle_list("omiai_list")


def save_omiai_list(data: Dict) -> None:
    _save_pickle_list(data, "omiai_list")


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
