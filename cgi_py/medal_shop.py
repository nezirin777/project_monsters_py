import sub_def
import conf


def medal_shop_ok(FORM):
    """メダル交換の処理を行う"""
    Conf = conf.Conf

    if "m_name" not in FORM:
        sub_def.error("対象が選択されていません。")
        return

    m_name = FORM["m_name"]

    Medal_lsit = sub_def.open_medal_shop_dat()
    user = sub_def.open_user()
    party = sub_def.open_party()

    if len(party) >= 10:
        sub_def.error("モンスターが一杯です！")

    item = Medal_lsit[m_name]
    price = item["price"]
    currency = "medal" if item["type"] == "メダル" else "money"

    if user[currency] < price:
        sub_def.error(f"{item['type']}が足りません！")
        return

    new_mob = sub_def.monster_select(m_name)
    party.append(new_mob)
    for i, pt in enumerate(party, 1):
        pt["no"] = i

    user[currency] -= price
    sub_def.save_user(user)
    sub_def.save_party(party)

    sub_def.print_result(
        f"""<img src="{Conf["imgpath"]}/{m_name}.gif"><span>{m_name}</span>が仲間に加わりました""",
        "",
        FORM["token"],
    )
