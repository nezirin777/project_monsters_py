# kakin_item.py - 課金アイテム処理（user_all 新形式対応版）

import time

from sub_def.file_ops import open_user_all, save_user_all


def kakin_item(item_id: str, user_name: str):
    """
    課金アイテム処理
    item_id: "boost1", "boost3", "boost7"
    user_name: 対象ユーザー名
    """
    if item_id not in ("boost1", "boost3", "boost7"):
        return False

    # user_all から全データを取得
    all_data = open_user_all(user_name)
    vips = all_data.setdefault("vips", {})  # "vips" キーがなければ空dictで初期化

    now_ts = time.time()

    # 追加する時間（秒）
    if item_id == "boost1":
        add_seconds = 3600 * 24  # 1日
    elif item_id == "boost3":
        add_seconds = 3600 * 24 * 3  # 3日
    elif item_id == "boost7":
        add_seconds = 3600 * 24 * 7  # 7日
    else:
        return False

    base = vips.get("boost")

    if base is not None and base > now_ts:
        vips["boost"] = base + add_seconds  # 延長
    else:
        vips["boost"] = now_ts + add_seconds  # 新規設定

    # 保存
    all_data["vips"] = vips
    save_user_all(all_data, user_name)

    return True
