from concurrent.futures import ThreadPoolExecutor, as_completed
import pickle
import os
import json
import sys

from sub_def.utils import error
from sub_def.file_ops import (
    get_file_path,
    open_csv_dict,
    open_csv_list,
    open_user_list,
)
import conf

# =============================
# 基本設定
# =============================
Conf = conf.Conf
datadir = Conf["savedir"]
progress_file = os.path.join(datadir, "progress.json")


# =============================
# CSV定義（完全統一管理）
# =============================
CSV_DEFS_MASTER = Conf.get("csv_defs_master", {})
CSV_DEFS_GLOBAL = Conf.get("csv_defs_global", {})
CSV_DEFS_USER = Conf.get("csv_defs_user", {})


# =============================
# ユーティリティ
# =============================
def log(msg):
    print(msg, file=sys.stderr)


def restore_empty_strings(obj):
    """None → 空文字へ変換（再帰対応）"""
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
    """pickle保存"""
    try:
        with open(path, "wb") as f:
            pickle.dump(obj, f)
    except Exception as e:
        raise RuntimeError(f"Pickle保存失敗: {path}: {e}")


def safe_remove(path):
    """安全なファイル削除"""
    try:
        if os.path.isfile(path):
            os.remove(path)
    except Exception as e:
        raise RuntimeError(f"ファイル削除失敗: {path}: {e}")


def filter_data(data, conf_def):
    """主キーで無効データ除外"""
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
# コア処理（単一CSV変換）
# =============================
def convert_csv_to_pickle(csv_name, user_name=None):
    """CSV → pickle変換（単体処理）"""
    # ---- 定義取得 ----
    if csv_name in CSV_DEFS_GLOBAL:
        conf_def = CSV_DEFS_GLOBAL.get(csv_name)
        category = "GLOBAL"

    elif csv_name in CSV_DEFS_USER:
        conf_def = CSV_DEFS_USER.get(csv_name)
        category = "USER"

    elif csv_name in CSV_DEFS_MASTER:
        conf_def = CSV_DEFS_MASTER.get(csv_name)
        category = "MASTER"

    else:
        log(f"[SKIP] 未定義CSV: {csv_name}")
        return

    # ---- pickle対象チェック ----
    if "pickle" not in conf_def:
        log(f"[SKIP] pickle未定義: {csv_name}")
        return

    pickle_name = conf_def["pickle"]
    data_type = conf_def.get("type", "list")

    # ---- パス生成 ----
    csv_path = get_file_path(csv_name, user_name)
    pickle_path = get_file_path(pickle_name, user_name if user_name else "")

    # ---- CSV存在チェック ----
    if not os.path.exists(csv_path):
        log(f"[SKIP] CSVなし: {csv_path}")
        return

    log(
        f"[START] {category} | {csv_name} → {pickle_name} | user={user_name} |data_type={data_type}"
    )

    # ---- 読み込み ----
    try:
        if data_type == "dict":
            data = open_csv_dict(csv_name, user_name)
        elif data_type == "single":
            data = open_csv_list(csv_name, user_name, single=True)
        else:
            data = open_csv_list(csv_name, user_name, single=False)
    except Exception as e:
        log(f"[ERROR] 読み込み失敗: {csv_name} | {e}")
        return

    # ---- フィルタ ----
    data = filter_data(data, conf_def)

    # ---- None補正 ----
    data = restore_empty_strings(data)

    # ---- 保存 ----
    try:
        os.makedirs(os.path.dirname(pickle_path), exist_ok=True)
        pickle_dump(data, pickle_path)
    except Exception as e:
        log(f"[ERROR] 保存失敗: {pickle_path} | {e}")
        return

    # ---- CSV削除（MASTERは保持）----
    if csv_name not in CSV_DEFS_MASTER:
        try:
            safe_remove(csv_path)
        except Exception as e:
            log(f"[WARN] CSV削除失敗: {csv_path} | {e}")

    log(f"[DONE] {category} | {csv_name}")


# =============================
# ユーザー単位処理
# =============================
def user_dat(user_name):
    """ユーザー単位で全CSV変換"""
    for csv_name, conf_def in CSV_DEFS_USER.items():
        convert_csv_to_pickle(csv_name, user_name)


# =============================
# 並列処理＋進捗管理
# =============================
def process_batch(users, process_func, batch_size=10):
    """並列処理＋進捗記録"""
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

            # 一定間隔で進捗保存
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
    """全ユーザー一括変換"""
    u_list = open_user_list()
    users = list(u_list.keys())

    errors = process_batch(users, user_dat)

    if errors:
        error("一部の変換に失敗しました\n" + "\n".join(errors[:5]))


# =============================
# エントリーポイント（完全統一）
# =============================
def csv_to_pickle(target_name):
    """
    統一エントリーポイント

    target_name:
        - "全員" → 全ユーザー
        - "user_list" など → グローバルCSV
        - ユーザー名 → そのユーザーのみ
    """
    # CSV名として直接処理
    if target_name in CSV_DEFS_GLOBAL:
        convert_csv_to_pickle(target_name)
        return

    # 全ユーザー
    if target_name == "全員":
        handle_all_users()
        return
    else:
        user_dat(target_name)
        return
