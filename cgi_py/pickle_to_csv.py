from concurrent.futures import ThreadPoolExecutor, as_completed
import sub_def
import conf
import os
import json

Conf = conf.Conf
datadir = Conf["savedir"]
progress_file = os.path.join(datadir, "progress.json")


def delete_progress_file():
    """進捗ファイルを削除"""
    try:
        if os.path.exists(progress_file):
            os.remove(progress_file)
    except Exception as e:
        sub_def.error(f"進捗ファイルの削除に失敗しました: {e}")


def save_user_data(in_name):
    """
    指定したユーザーのデータを個別のCSVファイルに保存する。
    """

    # 各データの保存

    park_data = sub_def.open_park(in_name)
    default_park_data = {
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
    park_data = [default_park_data] if not park_data else park_data

    sub_def.save_csv(park_data, "park.csv", in_name)
    sub_def.save_csv(sub_def.open_room_key(in_name), "room_key.csv", in_name)
    sub_def.save_csv(sub_def.open_party(in_name), "party.csv", in_name)
    sub_def.save_csv(sub_def.open_user(in_name), "user.csv", in_name)
    sub_def.save_csv(sub_def.open_vips(in_name), "vips.csv", in_name)
    sub_def.save_csv(sub_def.open_waza(in_name), "waza.csv", in_name)
    sub_def.save_csv(sub_def.open_zukan(in_name), "zukan.csv", in_name)


def handle_all_users():
    u_list = sub_def.open_user_list()
    total_users = len(u_list)  # 全体のユーザー数

    # 初期化
    progress = {"total": total_users, "completed": 0, "status": "running"}
    with open(progress_file, mode="w", encoding="utf-8") as ff:
        json.dump(progress, ff)

    batch_size = 10
    completed = 0
    # 並列処理
    with ThreadPoolExecutor(max_workers=8) as executor:
        future_to_user = {
            executor.submit(save_user_data, name): name for name in u_list.keys()
        }

        for future in as_completed(future_to_user):
            name = future_to_user[future]
            try:
                future.result()  # エラーが発生した場合はここでキャッチ
            except Exception as e:
                sub_def.error(f"{name} 変換失敗: {e}")

            completed += 1
            if completed % batch_size == 0 or completed == total_users:
                progress["completed"] = completed
                with open(progress_file, mode="w", encoding="utf-8") as ff:
                    json.dump(progress, ff)

    delete_progress_file()


def pickle_to_csv(target_name):
    """
    指定されたターゲット名に基づいてデータをCSVに変換し、ファイルとして保存する。
    """
    # user_listのCSV変換
    if target_name == "user_list":
        sub_def.save_csv(
            sub_def.open_user_list(),
            "user_list.csv",
            "",
            "user_name",
        )

    # omiai_listのCSV変換
    elif target_name == "omiai_list":
        sub_def.save_csv(
            sub_def.open_omiai_list(),
            "omiai_list.csv",
            "",
            "user_name",
        )

    # 全ユーザーデータのCSV変換
    elif target_name == "全員":
        handle_all_users()
    # 個別ユーザーのデータ保存
    else:
        save_user_data(target_name)
