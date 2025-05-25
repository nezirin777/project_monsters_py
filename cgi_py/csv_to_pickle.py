from concurrent.futures import ThreadPoolExecutor, as_completed
import pickle
import os
import glob
import json

import sub_def
import conf

Conf = conf.Conf
datadir = Conf["savedir"]
progress_file = os.path.join(datadir, "progress.json")

# CSVファイルと対応するPickleファイルの辞書（形式を明示）
CSV_FILES = {
    "waza.csv": ("waza.pickle", "dict"),  # 辞書形式
    "zukan.csv": ("zukan.pickle", "dict"),  # 辞書形式
    "room_key.csv": ("room_key.pickle", "dict"),  # 辞書形式
    "park.csv": ("park.pickle", "list"),  # リスト形式
    "party.csv": ("party.pickle", "list"),  # リスト形式
    "user.csv": ("user.pickle", "single"),  # 単一レコード
    "vips.csv": ("vips.pickle", "single"),  # 単一レコード
    "user_list.csv": ("user_list.pickle", "dict"),  # 辞書形式
    "omiai_list.csv": ("omiai_list.pickle", "dict"),  # 辞書形式
}


def restore_empty_strings(obj):
    """辞書やリスト内の None を "" に置き換える"""
    if isinstance(obj, dict):
        return {k: ("" if v is None else v) for k, v in obj.items()}
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


def delete_progress_file():
    """進捗ファイルを削除"""
    try:
        if os.path.exists(progress_file):
            os.remove(progress_file)
    except Exception as e:
        sub_def.error(f"進捗ファイルの削除に失敗しました: {e}")


def remove_glob(path, recursive=True):
    """指定パスのファイルを削除"""
    for p in glob.glob(path, recursive=recursive):
        if os.path.isfile(p):
            os.remove(p)


def pickle_dump(obj, path):
    """オブジェクトをPickle形式で保存"""
    try:
        with open(path, mode="wb") as f:
            pickle.dump(obj, f)
    except IOError as e:
        sub_def.error(f"Pickleファイルの保存に失敗しました: {path}: {e}")


def convert_csv_to_pickle(csv_name, pickle_name, data_type, user_name=None):
    """CSVからPickle形式への変換を行う汎用関数"""
    try:
        # ファイルパスの決定
        csv_path = sub_def.get_file_path(csv_name, user_name)
        pickle_path = sub_def.get_file_path(
            pickle_name, user_name if user_name else "", dir_type="savedir"
        )

        if not os.path.exists(csv_path):
            return  # CSVファイルが存在しない場合はスキップ

        # データの取得
        if data_type == "dict":
            data = sub_def.open_csv_dict(csv_name, user_name)
        elif data_type == "single":
            data = sub_def.open_csv_list(csv_name, user_name, single=True)
        else:  # list
            data = sub_def.open_csv_list(csv_name, user_name, single=False)

        # データフィルタリング（必要に応じて）
        if isinstance(data, list):
            data = [v for v in data if v.get("name") not in ("", "-", "0")]
        elif isinstance(data, dict):
            data = {k: v for k, v in data.items() if k not in ("", "-", "0")}

        # None を "" に戻す
        data = restore_empty_strings(data)

        # Pickleファイルに保存
        os.makedirs(os.path.dirname(pickle_path), exist_ok=True)
        pickle_dump(data, pickle_path)

        # 元のCSVファイルを削除
        remove_glob(csv_path)

    except Exception as e:
        sub_def.error(f"CSV変換エラー: {csv_name} -> {pickle_name}: {e}")


def user_dat(user_name):
    """特定のユーザーのデータをCSVからPickleに変換"""
    for csv_name, (pickle_name, data_type) in CSV_FILES.items():
        if csv_name not in [
            "user_list.csv",
            "omiai_list.csv",
        ]:  # グローバルファイルを除外
            convert_csv_to_pickle(csv_name, pickle_name, data_type, user_name)


def handle_all_users():
    """全ユーザーのデータをPickle変換"""
    u_list = sub_def.open_user_list()
    total_users = len(u_list)

    batch_size = 10
    completed = 0
    progress = {"total": total_users, "completed": 0, "status": "running"}
    with open(progress_file, mode="w", encoding="utf-8") as ff:
        json.dump(progress, ff)

        # 並列処理でユーザーごとのデータを変換
        with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
            futures = {executor.submit(user_dat, name): name for name in u_list}

            for completed, future in enumerate(as_completed(futures), 1):
                try:
                    future.result()  # 各スレッドの処理結果を取得
                except Exception as e:
                    sub_def.error(f"{futures[future]} 変換失敗: {e}")

                if completed % batch_size == 0 or completed == total_users:
                    progress["completed"] = completed
                    with open(progress_file, mode="w", encoding="utf-8") as ff:
                        json.dump(progress, ff)

        delete_progress_file()


def csv_to_pickle(target_name):
    """指定されたターゲットのCSVデータをPickleに変換"""
    if target_name in {"user_list", "omiai_list"}:
        pickle_name, data_type = CSV_FILES[f"{target_name}.csv"]
        convert_csv_to_pickle(f"{target_name}.csv", pickle_name, data_type)
    elif target_name == "全員":
        handle_all_users()
    else:
        user_dat(target_name)
