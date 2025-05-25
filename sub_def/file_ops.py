# file_ops.py

from pathlib import Path
import os
import datetime
import pandas as pd
import pickle
from typing import Dict, List, Any
from functools import lru_cache

import conf
import exLock

from .utils import error
from .crypto import get_session

lock = exLock.exLock("./lock_fol")
Conf = conf.Conf

PICKLE_DIR = "pickle"
# ログ設定
LOGFILE = Path(Conf["savedir"]) / "bbslog.log"
MAX_LOG_LINES = Conf["max_log_lines"]


# ===========#
# BBS関係    #
# ===========#
def ensure_logfile() -> None:
    """ログファイルの存在を保証"""
    if not LOGFILE.exists():
        LOGFILE.parent.mkdir(parents=True, exist_ok=True)
        LOGFILE.write_text("", encoding="utf-8")


@lru_cache(maxsize=1)
def read_log() -> str:
    """ログを読み込み、逆順（最新を先頭）に"""
    try:
        lines = LOGFILE.read_text(encoding="utf-8").splitlines()
        return "".join(lines[::-1])
    except (FileNotFoundError, IOError):
        return ""


def append_log(newlog: str) -> None:
    """ログを末尾に追記、最大行数を制限"""
    lock = exLock.exLock(os.path.join(Conf["savedir"], "lock_log"))
    lock.lock()
    try:
        with LOGFILE.open("a", encoding="utf-8") as f:
            f.write(newlog)
        read_log.cache_clear()
        with LOGFILE.open("r", encoding="utf-8") as f:
            lines = f.readlines()
        if len(lines) > MAX_LOG_LINES:
            with LOGFILE.open("w", encoding="utf-8") as f:
                f.writelines(lines[-MAX_LOG_LINES:])
    except IOError as e:
        error(f"ログ操作に失敗しました: {e}")
    finally:
        lock.unlock()


# ===================#
# ファイル操作ヘルパー #
# ===================#
def _handle_file_error(operation: str, file_path: str, e: Exception) -> None:
    if isinstance(e, FileNotFoundError):
        error(f"{operation}ファイルが見つかりません: {file_path}", 99)
    elif isinstance(e, (pickle.UnpicklingError, pd.errors.EmptyDataError)):
        error(f"{operation}ファイルの読み込みに失敗しました: {file_path}", 99)
    else:
        error(f"{operation}中にエラーが発生しました: {e}", 99)


def get_file_path(file: str, user: str = "", dir_type: str = "savedir") -> str:
    """ファイルパスを生成"""
    base_dir = Conf["savedir"] if dir_type == "savedir" else Conf["datdir"]
    if user and dir_type == "savedir":
        return os.path.join(base_dir, user, PICKLE_DIR, f"{file}.pickle")
    return os.path.join(base_dir, file)


@lru_cache(maxsize=128)
def get_pickle_file_path(file: str, user: str = "") -> str:
    s = get_session()
    name = user or s.get("in_name") or ""
    if not name:
        error(
            f"pickleファイル操作エラー: ユーザー名が存在していません。{file}/ユーザー名：{name}",
            99,
        )
    return get_file_path(file, name)


def pickle_load(file: str, user: str = "") -> Any:
    file_path = get_pickle_file_path(file, user)
    try:
        with open(file_path, mode="rb") as f:
            return pickle.load(f)
    except Exception as e:
        _handle_file_error("pickle", file_path, e)
        raise


def pickle_dump(data: Any, file: str, user: str = "") -> None:
    file_path = get_pickle_file_path(file, user)
    lock = exLock.exLock(os.path.join(Conf["savedir"], user, "lock_fol"))
    lock.lock()
    try:
        with open(file_path, mode="wb") as f:
            pickle.dump(data, f)
    except Exception as e:
        _handle_file_error("pickle", file_path, e)
    finally:
        lock.unlock()


def _create_pickle_accessor(file_name: str):
    def load(user=""):
        return pickle_load(file_name, user)

    def dump(data, user=""):
        pickle_dump(data, file_name, user)

    return load, dump


def initialize_pickle(file_name: str, initial_data=None):
    """任意のpickleファイルを初期化"""
    initial_data = initial_data or {}
    lock.lock()
    try:
        file_path = os.path.join(Conf["savedir"], file_name)
        with open(file_path, mode="wb") as f:
            pickle.dump(initial_data, f)
    except Exception as e:
        error(f"pickleファイルの初期化に失敗しました: {e}", 99)
    finally:
        lock.unlock()


def _load_pickle_list(file: str) -> Dict:
    """pickleリストを読み込み、初期化"""
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
    """pickleリストを安全に保存"""
    import tempfile
    import shutil

    file_path = os.path.join(Conf["savedir"], f"{file}.pickle")
    with tempfile.NamedTemporaryFile(mode="wb", delete=False) as temp_file:
        pickle.dump(data, temp_file)
        temp_file.flush()
        os.fsync(temp_file.fileno())
        temp_file_path = temp_file.name
    lock.lock()
    try:
        shutil.move(temp_file_path, file_path)
    except Exception as e:
        error(f"{file}の保存中にエラーが発生しました: {e}", 99)
    finally:
        lock.unlock()


# ===============#
# CSV操作       #
# ===============#
def get_csv_file_path(file: str, name: str = "") -> str:
    return get_file_path(file, name) if name else get_file_path(file)


def open_csv_dict(file: str, name: str = "") -> Dict:
    """CSVを辞書形式で読み込み"""
    file_path = get_csv_file_path(file, name)
    index_col = "user_name" if file in ["user_list.csv", "omiai_list.csv"] else "name"
    sort_val = None if file in ["user_list.csv", "omiai_list.csv"] else True
    try:
        df = pd.read_csv(
            file_path,
            encoding="utf-8_sig",
            index_col=index_col,
            na_filter=False,
        ).convert_dtypes()
        if sort_val:
            df.sort_values("no")
        return df.to_dict(orient="index")
    except Exception as e:
        _handle_file_error("CSV", file_path, e)
        return {}


def open_csv_list(file: str, name: str = "", single: bool = False) -> List | Dict:
    """CSVをリスト形式で読み込み"""
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

    # 文字列と欠損値の処理（既存ロジックを維持）
    string_cols = [col for col in df.columns if pd.api.types.is_string_dtype(df[col])]
    nullable_cols = [
        col for col in df.columns if df[col].isnull().any() and col not in string_cols
    ]
    if string_cols:
        df[string_cols] = df[string_cols].fillna("")
    if nullable_cols:
        for col in nullable_cols:
            non_na_values = df[col].dropna()
            if (
                non_na_values.empty
                or non_na_values.apply(
                    lambda x: x == int(x) if pd.notnull(x) else True
                ).all()
            ):
                df[col] = df[col].astype("Int64")
            else:
                df[col] = df[col].astype("Float64")

    dic = df.to_dict(orient="records")
    return dic[0] if single else dic


def save_csv(data: Any, file: str, name: str = "", label: str = "name") -> None:
    file_path = get_csv_file_path(file, name)
    if not data:
        error("対象のデータは空っぽのようです。<br>出力できませんでした。", 99)
        return

    index = False
    index_label = None
    try:
        if isinstance(data, pd.DataFrame):
            df = data
        elif isinstance(data, dict):
            if any(isinstance(v, dict) for v in data.values()):
                df = pd.DataFrame.from_dict(data, orient="index")
                index = True
                index_label = label
            else:
                df = pd.DataFrame([data])
        elif isinstance(data, list) and all(isinstance(item, dict) for item in data):
            df = pd.DataFrame(data)
        else:
            error("データの形式がサポートされていません。", 99)
            return
        df.to_csv(file_path, index=index, index_label=index_label, encoding="utf-8_sig")
    except Exception as e:
        _handle_file_error("CSV", file_path, e)


# ================#
# データファイル  #
# ================#
def open_dat(file: str) -> Dict:
    file_path = os.path.join(Conf["datdir"], PICKLE_DIR, f"{file}.pickle")
    if not os.path.exists(file_path):
        error(f"ファイルが見つかりませんよ: {file_path}", 99)
        return {}
    try:
        with open(file_path, mode="rb") as f:
            data = pickle.load(f)
        return dict(sorted(data.items(), key=lambda x: x[1]["no"]))
    except (pickle.UnpicklingError, KeyError) as e:
        error(f"データの読み込み中にエラーが発生しました: {e}", 99)
        return {}


def _create_dat_opener(file_name: str):
    def opener():
        return open_dat(file_name)

    return opener


# =====================================================================================================#
# ファイルopen_user_list                                                                                #
# user_name,pass,host,bye,key,m1_name,m1_hai,m1_lv,m2_name,m2_hai,m2_lv,m3_name,m3_hai,m3_lv,money,mes #
# =====================================================================================================#
def open_user_list():
    """ユーザーリストを読み込み、ランキングを更新"""
    user_list = _load_pickle_list("user_list")
    if user_list:
        sorted_items = sorted(
            user_list.items(), key=lambda x: x[1].get("key", 0), reverse=True
        )
        user_list = {k: v for k, v in sorted_items}
        for i, (key, value) in enumerate(user_list.items(), start=1):
            user_list[key]["rank"] = i
    return user_list


def save_user_list(user_list):
    """ユーザーリストを保存"""
    _save_pickle_list(user_list, "user_list")


# ========================================================================#
# おみあい所登録データ                                                      #
# user,pass,name,lv,mlv,hai,hp,mhp,mp,mmp,atk,def,agi,ex,nex,sei,sex,mes  #
# =========================================================================#
def open_omiai_list():
    """お見合いリストを読み込み"""
    return _load_pickle_list("omiai_list")


def save_omiai_list(omiai_list):
    """お見合いリストを保存"""
    _save_pickle_list(omiai_list, "omiai_list")


# =========================#
# メダル杯開催時間ファイル  #
# =========================#
class TournamentScheduler:
    """トーナメント日付を管理"""

    FILE_PATH = os.path.join(Conf["savedir"], "tournament_time.txt")
    FORMAT = "%Y年%m月%d日"

    @staticmethod
    def calculate_next_date(today: datetime.date = None) -> str:
        today = today or datetime.date.today()
        day = today.day
        if 1 <= day < 11:
            next_day = 11
        elif 11 <= day < 21:
            next_day = 21
        else:
            next_day = 1
            next_month = today.month % 12 + 1
            next_year = today.year + (today.month // 12)
            today = today.replace(year=next_year, month=next_month)
        next_date = today.replace(day=next_day)
        return next_date.strftime(TournamentScheduler.FORMAT)

    @staticmethod
    def save_date(date_str: str) -> None:
        with open(TournamentScheduler.FILE_PATH, mode="w", encoding="utf-8") as f:
            f.write(date_str)

    @staticmethod
    def load_date() -> str:
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


def timesyori():
    """次のトーナメント日付を計算して保存"""
    date_str = TournamentScheduler.calculate_next_date()
    TournamentScheduler.save_date(date_str)
    return date_str


def open_tournament_time():
    """トーナメント日付を読み込み"""
    return TournamentScheduler.load_date()


@lru_cache(maxsize=1)
def get_tournament_status():
    """トーナメント日時と残日数を返す"""
    t_time = open_tournament_time()
    try:
        t_date = datetime.datetime.strptime(t_time, "%Y年%m月%d日")
        t_count = (t_date - datetime.datetime.now()).days
        return {"t_time": t_time, "t_count": t_count}
    except ValueError as e:
        timesyori()
        return {"t_time": open_tournament_time(), "t_count": 0}


open_user, save_user = _create_pickle_accessor("user")
open_party, save_party = _create_pickle_accessor("party")
open_park, save_park = _create_pickle_accessor("park")
open_vips, save_vips = _create_pickle_accessor("vips")
open_waza, save_waza = _create_pickle_accessor("waza")
open_room_key, save_room_key = _create_pickle_accessor("room_key")
open_zukan, save_zukan = _create_pickle_accessor("zukan")
open_battle, save_battle = _create_pickle_accessor("battle")

open_monster_dat = _create_dat_opener("monster_dat")
open_monster_boss_dat = _create_dat_opener("monster_boss_dat")
open_key_dat = _create_dat_opener("key_dat")
open_tokugi_dat = _create_dat_opener("tokugi_dat")
open_seikaku_dat = _create_dat_opener("seikaku_dat")
open_book_dat = _create_dat_opener("book_dat")
open_medal_shop_dat = _create_dat_opener("medal_shop_dat")
open_vips_shop_dat = _create_dat_opener("vips_shop_dat")
open_vips_shop2_dat = _create_dat_opener("vips_shop2_dat")


# ============================================================================#
# モンスターデータ                                                              #
# no,name,hp,mp,atk,def,agi,exp,money,waza,type,m_type,room,階層A,階層B,get    #
# 血統1,相手1,血統2,相手2,血統3,相手3,お見合いA1,お見合いB1,お見合いA2,お見合いB2  #
# ============================================================================#
# 鍵データ                                 #
# no,type,name1,name2 name1=鍵,name2=部屋 #
# =======================================#
# 特技データ             #
# no,name,mp,damage,type#
# ==============================#
# 性格データ                    #
# no,name,勇気,優しさ,知性,行動 #
# =========================#
# 本データ                 #
# no,name,勇気,優しさ,知性  #
# =========================#
# メダル交換所             #
# no,name,price,type      #
# =========================#
# =========================#
# vips交換所               #
# no,name,price,type      #
# =====================================#
# ユーザーデータ                      #
# name,pass,key,medal,money,mes,getm #
# =====================================#
# ===============================================================#
# パーティー                                                     #
# no,name,lv,mlv,hai,hp,mhp,mp,mmp,atk,def,agi,exp,n_exp,sei,sex#
# ===============================================================#
# モンスターパーク                                           #
# name,lv,mlv,hai,hp,mhp,mp,mmp,atk,def,agi,ex,nex,sei,sex #
# ==========================================================#
# vipsデータ                   #
# =============================#
# 習得特技          #
# no,name,type,get #
# ==================#
# =========================#
# 所持鍵                   #
# no,type,name1,name2,get #
# =========================#
# 図鑑                     #
# no,name,m_type,get       #
# ======================================================#
# 戦闘一時データ                                        #
# no,name,name2,hp,mhp,mp,mmp,atk,def,agi,exp,money,sex#
# ======================================================#
