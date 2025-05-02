import sub_def
import conf

Conf = conf.Conf


def omiai_touroku(FORM):
    # 必須フィールドの取得とエラーチェック
    in_name = FORM.get("name")
    if not in_name:
        sub_def.error("名前が指定されていません")

    haidou1 = FORM.get("haigou1")
    if not haidou1:
        sub_def.error("モンスター番号が指定されていません")

    try:
        # 配列の位置合わせのため-1
        no = int(haidou1) - 1
    except ValueError:
        sub_def.error("無効なモンスター番号が指定されました")

    mes = FORM.get("mes", "")
    token = FORM["token"]

    party = sub_def.open_party()
    omiai_list = sub_def.open_omiai_list()

    if len(party) == 1:
        sub_def.error("パーティーに1体しかいない場合お見合いに参加することはできません")

    if party[no]["lv"] < Conf["haigoulevel"]:
        sub_def.error("お見合い可能Lvに達していないため登録できません。")

    # モンスター情報の更新
    omiai_list[in_name] = party[no].copy()  # party[no] のコピーを作成
    omiai_list[in_name].update({"mes": mes, "cancel": "", "request": "", "baby": ""})

    txt = f"""{party[no]["name"]}を登録しました。"""

    del party[no]
    for i, pt in enumerate(party, 1):
        pt["no"] = i

    sub_def.save_party(party)
    sub_def.save_omiai_list(omiai_list)

    html = f"""
        <form action="{{ Conf.cgiurl }}" method="post">
        <input type="hidden" name="mode" value="omiai_room">
        <input type="hidden" name="token" value="{token}">
        <button type="submit">お見合い所に戻る</button>
        </form>
    """
    sub_def.print_result(txt, html, FORM["token"])


def omiai_touroku_cancel(FORM):
    in_name = FORM.get("name")
    target = FORM.get("target")
    token = FORM.get("token")
    mes = FORM.get("mes", "")

    if not in_name or not target or not token:
        sub_def.error("名前、ターゲット、またはトークンが指定されていません")

    party = sub_def.open_party()
    omiai_list = sub_def.open_omiai_list()

    # 指定されたお見合い情報を取得
    omiai = omiai_list.get(in_name)
    if not omiai:
        sub_def.error("指定されたお見合い情報が存在しません")

    # 申請中のチェック
    if omiai["request"]:
        sub_def.error("他のユーザーに申請を出している場合登録をキャンセルできません。")

    # 申請されている場合のチェック
    for v in omiai_list.values():
        if v["request"] == target:
            sub_def.error(
                "あなたへのお見合い申請がある場合登録をキャンセルできません。"
            )

    if len(party) >= 10:
        sub_def.error("パーティがいっぱいで連れていくことができませんでした。")

    del omiai["mes"], omiai["cancel"], omiai["request"], omiai["baby"]

    party.append(omiai)

    mes = f"""<span>{omiai["name"]}</span>をパーティに加えました。"""

    for i, pt in enumerate(party, 1):
        pt["no"] = i
    del omiai_list[in_name]

    sub_def.save_party(party)
    sub_def.save_omiai_list(omiai_list)

    html = f"""
        <form action="{{ Conf.cgiurl }}" method="post">
            <input type="hidden" name="mode" value="omiai_room">
            <input type="hidden" name="token" value="{token}">
            <button type="submit">お見合い所に戻る</button>
        </form>
    """
    sub_def.print_result(mes, html, FORM["token"])
