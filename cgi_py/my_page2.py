def my_page2(FORM):
    import sub_def
    import conf

    Conf = conf.Conf

    in_name = FORM.get("name")
    token = FORM.get("token")

    user = sub_def.open_user(in_name)
    party = sub_def.open_party(in_name)

    user_v = sub_def.slim_number(user)

    # 追加情報を生成
    isekai = "hidden" if not user.get("isekai_limit") else ""

    option_list = list(range(1, len(party) + 1))
    party_with_index = list(enumerate(sub_def.slim_number(party), 1))

    # 必要な変数を辞書にまとめてテンプレートへ渡す
    content = {
        "script": {
            "party": "/" + "/".join(pt["name"] for pt in party),
        },
        "in_name": in_name,
        "token": token,
        "isekai": isekai,
        "user": user,
        "user_v": user_v,
        "party_with_index": party_with_index,
        "option_list": option_list,
    }

    sub_def.print_html("my_page_tmp.html", content)
