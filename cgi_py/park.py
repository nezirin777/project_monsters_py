import sub_def
import conf

Conf = conf.Conf


# ソート処理関数
def sort_park(park, sort_v):
    if sort_v == 1:
        park.sort(key=lambda x: x["name"])
        for i, ppt in enumerate(park, 1):
            ppt["no"] = i
        sub_def.save_park(park)
    elif sort_v == 2:
        mlist = sub_def.open_monster_dat()
        tmp = []
        for name in mlist.keys():
            for p in park:
                if name == p["name"]:
                    tmp.append(p)
        park = tmp
        for i, ppt in enumerate(park, 1):
            ppt["no"] = i
        sub_def.save_park(park)
    return park


# モンスターパーク表示関数
def park(FORM):

    page = int(FORM.get("page", 1))
    sort_v = int(FORM.get("sort_v", 0))
    token = FORM["s"]["token"]

    # 各種データを取得
    party = sub_def.open_party()
    park = sub_def.open_park()
    vips = sub_def.open_vips()

    if not vips.get("パーク", 0):
        sub_def.error("モンスターパークを所有していません。")

    # パーク容量と預かり状況
    waku = int(vips["パーク"] * 5)
    azukari = len(park)

    # ソート処理
    park = sort_park(park, sort_v)
    park_v = sub_def.slim_number_with_cookie(park)

    p1 = (page - 1) * 10
    p2 = min(page * 10, waku)
    jump_count = -(-len(park) // 10)

    content = {
        "Conf": Conf,
        "token": token,
        "azukari": azukari,
        "waku": waku,
        "party": party,
        "park_v": park_v,
        "jump_count": jump_count,
        "p1": p1,
        "p2": p2,
        "script": {
            "party": "/" + "/".join(pt["name"] for pt in party),
        },
    }

    sub_def.print_html("park_tmp.html", content)


# ====================##====================##====================##====================##====================#
# 手持ちを預ける
def park_1(FORM):

    # 配列位置を合わせるため-1
    Mno = int(FORM["Mno"]) - 1
    token = FORM["s"]["token"]

    party = sub_def.open_party()
    park = sub_def.open_park()
    vips = sub_def.open_vips()

    waku = vips["パーク"] * 5

    if len(park) >= waku:
        sub_def.error("パークがいっぱいで預けることができませんでした。")

    if len(party) == 1:
        sub_def.error(
            "パーティーがいなくなってしまいます。<br>預けることができません。"
        )

    mes = f"""<span>{party[Mno]["name"]}</span>を預けました。"""

    # 更新と保存
    park.append(party.pop(Mno))
    for i, pt in enumerate(party, 1):
        pt["no"] = i
    for i, ppt in enumerate(park, 1):
        ppt["no"] = i
    sub_def.save_park(park)
    sub_def.save_party(party)

    html = f"""
        <form action="{ Conf.cgi_url }" method="post">
        <input type="hidden" name="mode" value="park">
        <input type="hidden" name="token" value="{token}">
        <button type="submit">パークに戻る</button>
        </form>
    """

    sub_def.print_result(mes, html, FORM["token"])


# ====================##====================##====================##====================##====================#
# パークから連れていく
def park_2(FORM):
    # 配列位置を合わせるため-1
    Mno = int(FORM["mob"]) - 1
    token = FORM["s"]["token"]

    party = sub_def.open_party()
    park = sub_def.open_park()

    # パーティーが満杯かどうか確認
    if len(party) >= 10:
        sub_def.error("パーティがいっぱいで連れていくことができませんでした。")
        return

    mes = f"""<span>{park[Mno]["name"]}</span>をパーティに加えました。"""
    party.append(park.pop(Mno))

    for i, pt in enumerate(party, 1):
        pt["no"] = i
    for i, ppt in enumerate(park, 1):
        ppt["no"] = i

    sub_def.save_party(party)
    sub_def.save_park(park)

    html = f"""
        <form action="{ Conf.cgi_url }" method="post">
        <input type="hidden" name="mode" value="park">
        <input type="hidden" name="token" value="{token}">
        <button type="submit">パークに戻る</button>
        </form>
    """

    sub_def.print_result(mes, html, FORM["token"])
