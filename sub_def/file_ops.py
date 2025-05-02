# # user_ops.py

from pathlib import Path
import sys
import os
import datetime
from dateutil.relativedelta import relativedelta
import pandas as pd
import pickle
from typing import Dict, List, Any, Optional
from functools import lru_cache

import conf
import exLock

from .utils import error
from .crypto import get_session

sys.stdout.reconfigure(encoding="utf-8")
sys.stdin.reconfigure(encoding="utf-8")
lock = exLock.exLock("./lock_fol")
Conf = conf.Conf

PICKLE_DIR = "pickle"
UTF8_SIG = "utf-8_sig"


# ===========#
# BBS関係     #
# ===========#
def ensure_logfile(logfile: Path) -> None:
    if not logfile.exists():
        logfile.write_text("", encoding=UTF8_SIG)


def read_log(logfile: Path) -> str:
    try:
        return logfile.read_text(encoding=UTF8_SIG)
    except (FileNotFoundError, IOError):
        return ""


def append_log(logfile: Path, newlog: str, max_lines: int) -> None:
    try:
        with logfile.open("r", encoding=UTF8_SIG) as f:
            lines = f.readlines()[: max_lines - 1]
        lines.insert(0, newlog)
        with logfile.open("w", encoding=UTF8_SIG) as f:
            f.writelines(lines)
    except IOError as e:
        error(f"ログ操作に失敗しました: {e}")


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


@lru_cache(maxsize=128)
def get_pickle_file_path(file: str, user: str = "") -> str:
    s = get_session()
    name = user or s.get("name") or ""
    if not name:
        error(
            f"pickleファイル操作エラー: ユーザー名が存在していません。{file}/ユーザー名：{name}",
            99,
        )
    return os.path.join(Conf["savedir"], name, PICKLE_DIR, f"{file}.pickle")


def pickle_load(file: str, user: str = "") -> Any:
    file_path = get_pickle_file_path(file, user)
    try:
        with open(file_path, mode="rb") as f:
            return pickle.load(f)
    except Exception as e:
        _handle_file_error("pickle", file_path, e)
        return None


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


# ===============#
# CSV操作       #
# ===============#
def get_csv_file_path(file: str, name: str = "") -> str:
    return (
        os.path.join(Conf["savedir"], name, file)
        if name
        else os.path.join(Conf["savedir"], file)
    )


def open_csv(
    file: str,
    name: str = "",
    flg: int = 0,
    flg2: int = 0,
    col_names: Optional[List[str]] = None,
) -> Dict | List:
    file_path = get_csv_file_path(file, name)
    index_col = "user_name" if file in ["user_list.csv", "omiai_list.csv"] else "name"
    sort_val = None if file in ["user_list.csv", "omiai_list.csv"] else True

    try:
        if flg2:
            df = pd.read_csv(
                file_path,
                encoding=UTF8_SIG,
                names=col_names,
                index_col=index_col,
                na_filter=False,
            ).convert_dtypes()
        else:
            df = (
                pd.read_csv(file_path, encoding=UTF8_SIG, na_filter=False)
                .dropna(how="all")
                .convert_dtypes()
            )
    except Exception as e:
        _handle_file_error("CSV", file_path, e)
        return {} if flg2 else [] if not flg else {}

    if flg2:
        if sort_val:
            df.sort_values("no")
        return df.to_dict(orient="index")

    # 空の場合は直接結果を返す
    if df.empty:
        return [{}] if flg else []

    # 文字列型と欠損値を含む列を事前に特定
    string_cols = [col for col in df.columns if pd.api.types.is_string_dtype(df[col])]
    nullable_cols = [
        col for col in df.columns if df[col].isnull().any() and col not in string_cols
    ]

    # 文字列型の処理
    if string_cols:
        df[string_cols] = df[string_cols].fillna("")

    # flotを使わないならこの二行だけでおｋ。
    # if nullable_cols:
    # df[nullable_cols] = df[nullable_cols].astype("Int64")

    # 欠損値を含む列をInt64またはFloat64に変換
    if nullable_cols:
        for col in nullable_cols:
            # 浮動小数点数が含まれるかチェック（NaNを除いた値に小数点があるか）
            non_na_values = df[col].dropna()
            if (
                non_na_values.empty
                or non_na_values.apply(
                    lambda x: x == int(x) if pd.notnull(x) else True
                ).all()
            ):
                df[col] = df[col].astype("Int64")  # 整数型として扱う
            else:
                df[col] = df[col].astype("Float64")  # 浮動小数点型として扱う

    dic = df.to_dict(orient="records")
    return dic[0] if flg else dic


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
        df.to_csv(file_path, index=index, index_label=index_label, encoding=UTF8_SIG)
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
    """ユーザーリストを読み込み、ランキングを更新して返す"""
    try:
        file_path = os.path.join(Conf["savedir"], "user_list.pickle")

        # ファイルが存在しない場合、新しく作成
        if not os.path.exists(file_path):
            initialize_pickle("user_list.pickle")

        with open(file_path, mode="rb") as f:
            user_list = pickle.load(f)

        # user_listが空でない場合のみソートしてランクを更新
        if user_list:
            sorted_items = sorted(
                user_list.items(), key=lambda x: x[1].get("key", 0), reverse=True
            )
            user_list = {k: v for k, v in sorted_items}

            # ランクを更新
            for i, (key, value) in enumerate(user_list.items(), start=1):
                user_list[key]["rank"] = i

        return user_list
    except Exception as e:
        error(f"ユーザーリストの読み込み中にエラーが発生しました: {e}", 99)
        return {}


def save_user_list(user_list):
    import tempfile
    import shutil

    """ユーザーリストを一時ファイル経由で安全に保存"""
    try:
        file_path = os.path.join(Conf["savedir"], "user_list.pickle")

        # 一時ファイルに保存してからファイルを置き換える
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as temp_file:
            pickle.dump(user_list, temp_file)
            temp_file.flush()
            os.fsync(temp_file.fileno())
            temp_file_path = temp_file.name

        lock.lock()
        try:
            shutil.move(temp_file_path, file_path)
        finally:
            lock.unlock()
    except Exception as e:
        error(f"ユーザーリストの保存中にエラーが発生しました: {e}", 99)


# ========================================================================#
# おみあい所登録データ                                                      #
# user,pass,name,lv,mlv,hai,hp,mhp,mp,mmp,atk,def,agi,ex,nex,sei,sex,mes  #
# =========================================================================#
def open_omiai_list():
    """お見合いリストを読み込んで返す"""
    file_path = os.path.join(Conf["savedir"], "omiai_list.pickle")

    # ファイルが存在しない場合、新しく作成
    if not os.path.exists(file_path):
        initialize_pickle("omiai_list.pickle")

    try:
        with open(file_path, mode="rb") as f:
            return pickle.load(f)
    except Exception as e:
        error(f"お見合いリストの読み込み中にエラーが発生しました: {e}", 99)
        return {}


def save_omiai_list(omiai_list):
    import tempfile
    import shutil

    """お見合いリストを一時ファイル経由で安全に保存"""
    try:
        file_path = os.path.join(Conf["savedir"], "omiai_list.pickle")

        # 一時ファイルに保存してからファイルを置き換える
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as temp_file:
            pickle.dump(omiai_list, temp_file)
            temp_file.flush()
            os.fsync(temp_file.fileno())
            temp_file_path = temp_file.name

        lock.lock()
        try:
            shutil.move(temp_file_path, file_path)
        finally:
            lock.unlock()
    except Exception as e:
        error(f"お見合いリストの保存中にエラーが発生しました: {e}", 99)


# =========================#
# メダル杯開催時間ファイル  #
# =========================#
def timesyori():
    """次のトーナメント日付を計算してファイルに保存"""
    today = datetime.date.today()
    day = today.day

    # 次のトーナメントの日を決定
    if 1 <= day < 11:
        next_day = 11
    elif 11 <= day < 21:
        next_day = 21
    else:
        next_day = 1
        today = today + relativedelta(months=1)

    # 日付を更新
    next_tournament_date = today.replace(day=next_day)
    formatted_date = next_tournament_date.strftime("%Y年%m月%d日")

    # ファイルに書き込み
    file_path = os.path.join(Conf["savedir"], "tournament_time.txt")
    with open(file_path, mode="w", encoding="utf-8") as f:
        f.write(formatted_date)

    return formatted_date


def open_tournament_time():
    """トーナメント日付をファイルから読み込み、必要なら再計算して返す"""
    file_path = os.path.join(Conf["savedir"], "tournament_time.txt")

    # ファイルが存在しない場合、新しい日付を生成
    if not os.path.exists(file_path):
        return timesyori()

    # ファイルから日付を読み込み
    try:
        with open(file_path, encoding="utf-8") as f:
            date_str = f.read().strip()

        # 日付のフォーマットを検証
        datetime.datetime.strptime(date_str, "%Y年%m月%d日")

    except (ValueError, OSError) as e:
        # 日付が無効または読み込みに失敗した場合、新しい日付を生成
        return timesyori()

    return date_str


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
