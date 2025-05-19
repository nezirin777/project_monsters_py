def seitenkan(FORM):
    import sub_def

    # 配列位置に合わせるため-1
    no = int(FORM["no"]) - 1
    token = FORM["token"]

    if no < 0:
        sub_def.error("対象が選択されていません。")

    user = sub_def.open_user()
    party = sub_def.open_party()

    # 配列範囲内か確認
    if no < 0 or no >= len(party):
        sub_def.error("選択された対象が無効です。")

    if user["money"] < party[no]["hai"] * 100:
        sub_def.error("お金が足りません")

    html = f"""
        <form action="{{ Conf.cgi_url }}" method="post">
            <button type="submit">変換する</button>
            <input type="hidden" name="mode" value="seitenkan_ok">
            <input type="hidden" name="no" value="{no}">
            <input type="hidden" name="token" value="{token}">
        </form>
    """

    sub_def.print_result("性別変換しますか？", html, FORM["token"])


def seitenkan_ok(FORM):
    import sub_def
    import conf

    Conf = conf.Conf

    # -1された値のためそのまま
    no = int(FORM["no"])

    user = sub_def.open_user()
    party = sub_def.open_party()

    # 範囲チェック
    if no < 0 or no >= len(party):
        sub_def.error("選択された対象が無効です。")

    pt = party[no]
    sexs = Conf["sex"]

    pt["sex"] = sexs[(sexs.index(pt["sex"]) + 1) % len(sexs)]

    user["money"] -= pt["hai"] * 100

    sub_def.save_user(user)
    sub_def.save_party(party)

    sub_def.print_result(f"{pt['name']}の陰陽転換が完了しました", "", FORM["token"])
