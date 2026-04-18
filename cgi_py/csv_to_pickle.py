# csv_to_pickle.py -

from concurrent.futures import ThreadPoolExecutor, as_completed
import pickle
import os
import json
import sys
import pandas as pd
from typing import Dict, List, Any

from sub_def.utils import error
from sub_def.file_ops import (
    get_file_path,
    open_user_list,
    _handle_file_error,
)

import conf

Conf = conf.Conf
datadir = Conf["savedir"]
progress_file = os.path.join(datadir, "progress.json")

CSV_DEFS_MASTER = Conf.get("csv_defs_master", {})
CSV_DEFS_GLOBAL = Conf.get("csv_defs_global", {})
CSV_DEFS_USER = Conf.get("csv_defs_user", {})


def log(msg):
    print(msg, file=sys.stderr)


def get_csv_conf(target_key: str):
    """CSV定義を統一取得"""
    if target_key in CSV_DEFS_MASTER:
        return CSV_DEFS_MASTER[target_key]
    if target_key in CSV_DEFS_GLOBAL:
        return CSV_DEFS_GLOBAL[target_key]
    if target_key in CSV_DEFS_USER:
        return CSV_DEFS_USER[target_key]
    return None


def open_csv_dict(target_key: str, name: str = "") -> Dict:
    """CSVをindex付きdictとして読み込む"""
    conf_def = get_csv_conf(target_key)

    # 常にベース名 + .csv でパスを取得
    csv_file_name = f"{target_key}.csv"
    file_path = get_file_path(csv_file_name, name)

    index_col = conf_def.get("index", "name") if conf_def else "name"

    # ソート制御（GLOBALだけ除外）
    sort_val = target_key not in CSV_DEFS_GLOBAL

    log(
        f"[変換toDict] 対象: {target_key} ({csv_file_name}) ｜｜ パス: {file_path} ｜｜ インデックス: {index_col}"
    )

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


def open_csv_list(target_key: str, name: str = "", single: bool = False) -> List | Dict:
    """CSVをレコード配列として読み込む。single=Trueなら先頭1件のみ返す"""
    csv_file_name = f"{target_key}.csv"
    file_path = get_file_path(csv_file_name, name)

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


def restore_empty_strings(obj):
    if isinstance(obj, dict):
        return {
            k: (
                restore_empty_strings(v)
                if isinstance(v, (dict, list))
                else ("" if v is None else v)
            )
            for k, v in obj.items()
        }
    elif isinstance(obj, list):
        return [
            (
                restore_empty_strings(v)
                if isinstance(v, (dict, list))
                else ("" if v is None else v)
            )
            for v in obj
        ]
    return obj


def pickle_dump(obj, path):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(obj, f, protocol=pickle.HIGHEST_PROTOCOL)
    except Exception as e:
        raise RuntimeError(f"Pickle保存失敗: {path}: {e}")


def safe_remove(path):
    try:
        if os.path.isfile(path):
            os.remove(path)
    except Exception as e:
        log(f"[WARN] ファイル削除失敗: {path}: {e}")


def filter_data(data, conf_def):
    key = conf_def.get("index", "name")
    if isinstance(data, list):
        return [
            v
            for v in data
            if isinstance(v, dict) and str(v.get(key, "")).strip() not in ("", "-", "0")
        ]
    elif isinstance(data, dict):
        return {k: v for k, v in data.items() if str(k).strip() not in ("", "-", "0")}
    return data


# =============================
# コア処理
# =============================
def convert_csv_to_pickle(target_key, user_name=None):
    """CSV → pickle変換"""
    # 1. GLOBAL判定（最優先）
    if target_key in CSV_DEFS_GLOBAL:
        conf_def = CSV_DEFS_GLOBAL[target_key]
        category = "GLOBAL"
    elif target_key in CSV_DEFS_USER:
        conf_def = CSV_DEFS_USER[target_key]
        category = "USER"
    elif target_key in CSV_DEFS_MASTER:
        conf_def = CSV_DEFS_MASTER[target_key]
        category = "MASTER"
    else:
        log(f"[SKIP] 未定義CSVキー: {target_key}")
        return

    data_type = conf_def.get("type", "list")

    # ==================== GLOBAL処理 ====================
    if category == "GLOBAL":
        csv_name = f"{target_key}.csv"
        pickle_name = f"{target_key}.pickle"

        csv_path = get_file_path(csv_name)
        pickle_path = get_file_path(pickle_name)

        if not os.path.exists(csv_path):
            log(f"[SKIP] CSVファイルが見つかりません: {csv_path}")
            return

        log(f"[START] GLOBAL | {csv_name} → {pickle_name}")

        try:
            if data_type == "dict":
                data = open_csv_dict(target_key)
            else:
                data = open_csv_list(target_key)
        except Exception as e:
            log(f"[ERROR] 読み込み失敗: {csv_name} | {e}")
            return

        data = filter_data(data, conf_def)
        data = restore_empty_strings(data)

        try:
            pickle_dump(data, pickle_path)
            log(f"[DONE] GLOBAL | {csv_name} → {pickle_name}")
            safe_remove(csv_path)
        except Exception as e:
            log(f"[ERROR] 保存失敗: {pickle_path} | {e}")
        return

    # ==================== USER処理 ====================
    if category == "USER" and user_name:
        convert_user_to_user_all(user_name)
        return

    log(f"[SKIP] 未対応: {target_key}")


def convert_user_to_user_all(user_name: str):
    """ユーザー個別CSV → user_all.pickle"""
    log(f"[START] USER_ALL | {user_name} → user_all.pickle")

    all_data = {
        "user": {},
        "party": [],
        "vips": {},
        "room_key": {},
        "waza": {},
        "zukan": {},
        "park": [],
    }

    try:
        # ベースのキー名（target_key）を指定して読み込み
        all_data["user"] = restore_empty_strings(
            open_csv_list("user", user_name, single=True) or {}
        )
        all_data["party"] = restore_empty_strings(
            open_csv_list("party", user_name) or []
        )
        all_data["vips"] = restore_empty_strings(
            open_csv_list("vips", user_name, single=True) or {}
        )
        all_data["room_key"] = restore_empty_strings(
            open_csv_dict("room_key", user_name) or {}
        )
        all_data["waza"] = restore_empty_strings(open_csv_dict("waza", user_name) or {})
        all_data["zukan"] = restore_empty_strings(
            open_csv_dict("zukan", user_name) or {}
        )
        all_data["park"] = restore_empty_strings(open_csv_list("park", user_name) or [])

    except Exception as e:
        log(f"[ERROR] {user_name} データ読み込み失敗: {e}")
        return

    user_all_path = get_file_path("user_all.pickle", user_name)

    try:
        pickle_dump(all_data, user_all_path)
        log(f"[DONE] USER_ALL | {user_name} → user_all.pickle")
    except Exception as e:
        log(f"[ERROR] user_all保存失敗: {user_name} | {e}")


def user_dat(user_name):
    convert_user_to_user_all(user_name)


# =============================
# 並列処理
# =============================
def process_batch(users, process_func, batch_size=10):

    total = len(users)
    progress = {"total": total, "completed": 0, "status": "running"}
    last_written = 0
    errors = []

    max_workers = min(32, (os.cpu_count() or 1))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_func, u): u for u in users}

        completed = 0
        for future in as_completed(futures):
            user = futures[future]
            try:
                future.result()
            except Exception as e:
                errors.append(f"{user}: {type(e).__name__}: {e}")

            completed += 1
            if completed - last_written >= batch_size or completed == total:
                progress["completed"] = completed
                try:
                    with open(progress_file, "w", encoding="utf-8") as f:
                        json.dump(progress, f)
                    last_written = completed
                except Exception as e:
                    errors.append(f"進捗書き込み失敗: {e}")

    progress["status"] = "done"
    try:
        with open(progress_file, "w", encoding="utf-8") as f:
            json.dump(progress, f)
    except Exception:
        pass

    return errors


# =============================
# 全ユーザー処理
# =============================
def handle_all_users():
    u_list = open_user_list()
    users = list(u_list.keys())
    errors = process_batch(users, user_dat)

    if errors:
        error("一部の変換に失敗しました\n" + "\n".join(errors[:10]))


# =============================
# エントリーポイント
# =============================
def csv_to_pickle(target_name):
    """メイン関数"""
    if target_name in CSV_DEFS_GLOBAL:
        convert_csv_to_pickle(target_name)
        return

    if target_name == "全員":
        handle_all_users()
        return

    # 特定ユーザー
    user_dat(target_name)
