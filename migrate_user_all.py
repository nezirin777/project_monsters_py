#!D:\Python\Python314\python.exe

# migrate_user_all.py - 最終修正版（user=None対策込み）

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
    open_user_list,
)
from sub_def.file_ops import _atomic_pickle_save_unlocked, get_file_path, get_user_lock


def migrate_single_user(in_name):
    if not in_name or not isinstance(in_name, str):
        return f"スキップ: 不正なユーザー名 ({in_name})"

    try:
        data = {
            "user": open_user(in_name),
            "party": open_party(in_name),
            "vips": open_vips(in_name),
            "room_key": open_room_key(in_name),
            "waza": open_waza(in_name),
        }
        data["updated_at"] = datetime.datetime.now().isoformat()

        file_path = get_file_path("user_all.pickle", in_name)

        lock = get_user_lock(in_name)
        if not lock.lock():
            return f"ロック取得失敗: {in_name}"

        try:
            _atomic_pickle_save_unlocked(data, file_path)
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
        print("全ユーザー移行が正常に完了しました！")

    print(f"完了時刻: {datetime.datetime.now()}")


if __name__ == "__main__":
    migrate_all_users()
