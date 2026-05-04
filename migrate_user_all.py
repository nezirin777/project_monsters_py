#!D:\Python\Python314\python.exe

# migrate_user_all.py

import sys
import os
import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from sub_def.file_ops import (
    open_user,
    open_party,
    open_vips,
    open_room_key,
    open_waza,
    open_zukan,
    open_park,
    open_user_list,
)
from sub_def.file_ops import _atomic_pickle_save_unlocked, get_file_path, get_user_lock


def migrate_single_user(in_name):
    if not in_name or not isinstance(in_name, str):
        return f"スキップ: 不正なユーザー名 ({in_name})"

    try:
        # 古いファイル群からデータをかき集める
        data = {
            "user": open_user(in_name),
            "party": open_party(in_name),
            "vips": open_vips(in_name),
            "room_key": open_room_key(in_name),
            "waza": open_waza(in_name),
            "park": open_park(in_name),
            "zukan": open_zukan(in_name),
        }
        data["updated_at"] = datetime.datetime.now().isoformat()

        # 新しい保存先パス
        file_path = get_file_path("user_all.pickle", in_name)

        lock = get_user_lock(in_name)
        if not lock.lock():
            return f"ロック取得失敗: {in_name}"

        try:
            # 新ファイル(user_all.pickle)への書き込み
            _atomic_pickle_save_unlocked(data, file_path)

            # --- ここから追加：不要になった古いpickleファイルの削除 ---
            # 新しいファイルへの保存が成功した時だけ削除を実行する
            old_files = [
                "user.pickle",
                "party.pickle",
                "vips.pickle",
                "room_key.pickle",
                "waza.pickle",
                "zukan.pickle",
                "park.pickle",
            ]

            for old_filename in old_files:
                old_filepath = get_file_path(old_filename, in_name)
                # ファイルが存在する場合のみ削除
                if os.path.exists(old_filepath):
                    try:
                        os.remove(old_filepath)
                    except OSError as e:
                        # 万が一削除に失敗しても、移行自体は成功しているので続行させる
                        print(
                            f"削除警告: {in_name} の {old_filename} を削除できませんでした ({e})",
                            file=sys.stderr,
                        )
            # ----------------------------------------------------

            return None  # 成功
        finally:
            lock.unlock()

    except Exception as e:
        return f"失敗: {in_name} → {type(e).__name__}: {e}"


def migrate_all_users():
    print("Content-Type: text/plain; charset=utf-8\n")
    print("=== ユーザー全データ移行スクリプト (最終版) ===\n")

    u_list = open_user_list()
    users = [name for name in u_list.keys() if name and isinstance(name, str)]

    total = len(users)
    print(f"対象ユーザー数: {total} 人（不正名を除外済み）\n")
    print("移行開始...\n", flush=True)

    if total == 0:
        print("対象ユーザーがいません。")
        return

    errors = []
    completed = 0

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(migrate_single_user, name): name for name in users}

        for future in as_completed(futures):
            user = futures[future]
            try:
                err = future.result()
                if err:
                    errors.append(err)
            except Exception as e:
                errors.append(f"致命的エラー: {user} - {type(e).__name__}: {e}")

            completed += 1
            if completed % 10 == 0 or completed == total:
                print(f"進捗: {completed}/{total} 完了", flush=True)

    print("\n=== 移行処理終了 ===")
    if errors:
        print(f"エラー/スキップ: {len(errors)} 件")
        for err in errors[:30]:
            print(err)
        if len(errors) > 30:
            print(f"... 他 {len(errors)-30} 件")
    else:
        print("全ユーザー移行および旧ファイルの削除が正常に完了しました！")

    print(f"完了時刻: {datetime.datetime.now()}")


if __name__ == "__main__":
    migrate_all_users()
