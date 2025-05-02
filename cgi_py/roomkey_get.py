def roomkey_get(FORM):
    import sub_def

    get_key = FORM.get("get_key")

    # get_keyが指定されていない場合のエラーハンドリング
    if not get_key:
        sub_def.error("エラーが発生しました。<br>roomkey_get")

    # room_keyのデータを取得
    room_key = sub_def.open_room_key()

    # get_keyがroom_keyに存在するかチェック
    if get_key not in room_key:
        sub_def.error(f"指定されたキー '{get_key}' が存在しません。<br>roomkey_get")

    # 該当するキーの "get" フラグを更新
    room_key[get_key]["get"] = 1
    sub_def.save_room_key(room_key)

    # 結果を出力
    sub_def.print_result(f"""{get_key}の部屋の鍵を入手した！""", "", FORM["token"])
