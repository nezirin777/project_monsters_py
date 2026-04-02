def kakin_item(item_id, user_name):
    from sub_def.file_ops import open_vips, save_vips
    import time

    vips = open_vips(user_name)

    if item_id == "boost1":
        now_ts = time.time()
        base = vips.get("boost")

        if base is not None and base > now_ts:
            vips["boost"] = base + (3600 * 24)  # 延長
        else:
            vips["boost"] = now_ts + (3600 * 24)  # 新規

        save_vips(vips, user_name)
        return True

    if item_id == "boost3":
        now_ts = time.time()
        base = vips.get("boost")

        if base is not None and base > now_ts:
            vips["boost"] = base + (3600 * 24 * 3)  # 延長
        else:
            vips["boost"] = now_ts + (3600 * 24 * 3)  # 新規

        save_vips(vips, user_name)
        return True

    if item_id == "boost7":
        now_ts = time.time()
        base = vips.get("boost")

        if base is not None and base > now_ts:
            vips["boost"] = base + (3600 * 24 * 7)  # 延長
        else:
            vips["boost"] = now_ts + (3600 * 24 * 7)  # 新規

        save_vips(vips, user_name)
        return True

    return False
