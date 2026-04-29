# roomkey_get.py -部屋の鍵を入手する


def roomkey_get(FORM):
    from sub_def.file_ops import open_user_all, save_user_all
    from sub_def.utils import error, success

    user_name = FORM["s"]["in_name"]
    get_key = FORM.get("get_key")

    # get_keyが指定されていない場合のエラーハンドリング
    if not get_key:
        error("エラーが発生しました。<br>roomkey_get", jump="my_page")

    # room_keyのデータを取得
    user_all = open_user_all(user_name)
    room_key = user_all.get("room_key", {})

    # get_keyがroom_keyに存在するかチェック
    if get_key not in room_key:
        error(
            f"指定されたキー '{get_key}' が存在しません。<br>roomkey_get",
            jump="my_page",
        )

    # 該当するキーの "get" フラグを更新
    room_key[get_key]["get"] = 1
    user_all["room_key"] = room_key
    save_user_all(user_all, user_name)

    # 結果を出力
    success(f"{get_key}の部屋の鍵を入手した！")
