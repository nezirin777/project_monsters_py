from concurrent.futures import ThreadPoolExecutor, as_completed
import pickle
import os
import glob
import sub_def
import conf
import json


Conf = conf.Conf
datadir = Conf["savedir"]
progress_file = os.path.join(datadir, "progress.json")


# CSVファイルと対応するPickleファイルの辞書
CSV_FILES = {
    "waza.csv": "waza.pickle",
    "zukan.csv": "zukan.pickle",
    "room_key.csv": "room_key.pickle",
    "park.csv": "park.pickle",
    "party.csv": "party.pickle",
    "user.csv": "user.pickle",
    "vips.csv": "vips.pickle",
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
        sub_def.error(f"Error saving pickle file {path}: {e}")


def convert_csv_to_pickle(csv_name, pickle_name, user_name=None):
    """CSVからPickle形式への変換を行う汎用関数"""
    try:
        # ファイルパスの決定
        csv_path = (
            os.path.join(datadir, user_name, csv_name)
            if user_name
            else os.path.join(datadir, csv_name)
        )
        pickle_path = (
            os.path.join(datadir, user_name, "pickle", pickle_name)
            if user_name
            else os.path.join(datadir, pickle_name)
        )

        if not os.path.exists(csv_path):
            return  # CSVファイルが存在しない場合はスキップ

        # データの取得
        data = sub_def.open_csv(
            csv_name,
            user_name,
            flg=(
                1
                if csv_name
                in ["user.csv", "vips.csv", "user_list.csv", "omiai_list.csv"]
                else 0
            ),
            flg2=(
                1
                if csv_name
                in [
                    "waza.csv",
                    "zukan.csv",
                    "room_key.csv",
                    "user_list.csv",
                    "omiai_list.csv",
                ]
                else 0
            ),
        )

        # データフィルタリング（必要に応じて）
        if isinstance(data, list):
            data = [v for v in data if v.get("name") not in ("", "-", "0")]
        elif isinstance(data, dict):
            data = {k: v for k, v in data.items() if k not in ("", "-", "0")}

        # None を "" に戻す
        data = restore_empty_strings(data)

        # Pickleファイルに保存
        os.makedirs(
            os.path.dirname(pickle_path), exist_ok=True
        )  # 必要に応じてディレクトリを作成
        pickle_dump(data, pickle_path)

        # 元のCSVファイルを削除
        # remove_glob(csv_path)

    except Exception as e:
        sub_def.error(f"{csv_name} の変換中にエラーが発生しました: {e}")


def user_dat(user_name):
    """特定のユーザーのデータをCSVからPickleに変換"""
    for csv_name, pickle_name in CSV_FILES.items():
        convert_csv_to_pickle(csv_name, pickle_name, user_name)


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
        with ThreadPoolExecutor(max_workers=8) as executor:
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
        convert_csv_to_pickle(f"{target_name}.csv", f"{target_name}.pickle")
    elif target_name == "全員":
        handle_all_users()
    else:
        user_dat(target_name)
