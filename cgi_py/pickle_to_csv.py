# pickle_to_csv.py -user_all.pickle から個別のCSVファイルに変換して保存するスクリプト

from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import json
import pandas as pd

from sub_def.file_ops import (
    open_user_all,
    open_user_list,
    open_omiai_list,
    get_file_path,
    log,
)
from sub_def.utils import error
import conf

Conf = conf.Conf
datadir = Conf["savedir"]
progress_file = os.path.join(datadir, "progress.json")


def delete_progress_file():
    try:
        if os.path.exists(progress_file):
            os.remove(progress_file)
    except Exception as e:
        print(f"[WARN] 進捗ファイル削除失敗: {e}", file=os.sys.stderr)


def save_csv(data, target_key: str, name: str = "", label: str = "name"):
    """データをCSVとして保存"""
    # ベース名（キー）に .csv をくっつけてパスを取得
    csv_file_name = (
        f"{target_key}.csv" if not target_key.endswith(".csv") else target_key
    )
    file_path = get_file_path(csv_file_name, name)

    if data is None:
        data = []

    if not data and not isinstance(data, (dict, list)):
        error("対象のデータは空っぽのようです。<br>出力できませんでした。", 99)
        return

    try:
        write_index = True
        if isinstance(data, pd.DataFrame):
            df = data
        elif isinstance(data, dict):
            if any(isinstance(v, dict) for v in data.values()):  # dict of dict
                df = pd.DataFrame.from_dict(data, orient="index")
                df.index.name = label
            else:  # single dict
                df = pd.DataFrame([data])
                write_index = False  # 単一辞書なら行番号不要
        elif isinstance(data, list) and data and isinstance(data[0], dict):
            df = pd.DataFrame(data)
            write_index = False  # リストなら行番号不要
        else:
            df = pd.DataFrame(data)
            write_index = False

        df.to_csv(
            file_path,
            index=write_index,
            index_label=(
                label
                if (write_index and getattr(df.index, "name", None) is None)
                else None
            ),
            encoding="utf-8_sig",
        )

        log(f"[CSV出力] {csv_file_name} (user={name or 'GLOBAL'}) → {len(df)} 件")

    except Exception as e:
        error(f"CSV書き込みエラー: {target_key} | {e}", 99)


def save_user_data(in_name: str):
    """user_all から個別CSVを生成"""
    try:
        all_data = open_user_all(in_name)

        user = all_data.get("user", {})
        party = all_data.get("party", [])
        vips = all_data.get("vips", {})
        room_key = all_data.get("room_key", {})
        waza = all_data.get("waza", {})
        zukan = all_data.get("zukan", {})
        park = all_data.get("park", [])

        if not park:
            default_park = {
                key: "-"
                for key in [
                    "no",
                    "name",
                    "lv",
                    "mlv",
                    "hai",
                    "hp",
                    "mhp",
                    "mp",
                    "mmp",
                    "atk",
                    "def",
                    "agi",
                    "exp",
                    "n_exp",
                    "sei",
                    "sex",
                ]
            }
            park = [default_park]

        # CSV出力 (ベース名で指定)
        save_csv(park, "park", in_name)
        save_csv(room_key, "room_key", in_name)
        save_csv(party, "party", in_name)
        save_csv(user, "user", in_name, label="name")
        save_csv(vips, "vips", in_name, label="name")
        save_csv(waza, "waza", in_name)
        save_csv(zukan, "zukan", in_name)

        log(f"[完了] {in_name}")

    except Exception as e:
        error(f"{in_name} のCSV出力失敗: {e}")


def handle_all_users():
    u_list = open_user_list()
    total_users = len(u_list)

    progress = {"total": total_users, "completed": 0, "status": "running"}
    with open(progress_file, "w", encoding="utf-8") as f:
        json.dump(progress, f)

    batch_size = 10
    completed = 0

    with ThreadPoolExecutor(max_workers=min(32, os.cpu_count() or 4)) as executor:
        futures = {
            executor.submit(save_user_data, name): name for name in u_list.keys()
        }

        for future in as_completed(futures):
            name = futures[future]
            try:
                future.result()
            except Exception as e:
                print(f"[ERROR] {name} CSV出力失敗: {e}", file=os.sys.stderr)

            completed += 1
            if completed % batch_size == 0 or completed == total_users:
                progress["completed"] = completed
                with open(progress_file, "w", encoding="utf-8") as f:
                    json.dump(progress, f)

    delete_progress_file()


def pickle_to_csv(target_name: str):
    """メインエントリポイント"""
    if target_name == "user_list":
        # ベース名 "user_list" で指定
        save_csv(open_user_list(), "user_list", "", label="user_name")

    elif target_name == "omiai_list":
        # ベース名 "omiai_list" で指定
        save_csv(open_omiai_list(), "omiai_list", "", label="user_name")

    elif target_name == "全員":
        handle_all_users()

    else:
        save_user_data(target_name)
