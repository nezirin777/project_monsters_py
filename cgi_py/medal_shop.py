from sub_def.file_ops import open_medal_shop_dat, open_user_all, save_user_all
from sub_def.monster_ops import monster_select
from sub_def.utils import error, success, info


import conf

Conf = conf.Conf


def medal_shop_ok(FORM):
    """メダル交換の処理を行う"""
    if "m_name" not in FORM:
        error("対象が選択されていません。", jump="medal_shop")

    m_name = FORM["m_name"]
    user_name = FORM["s"]["in_name"]

    user_all = open_user_all(user_name)

    Medal_lsit = open_medal_shop_dat()

    user = user_all["user"]
    party = user_all["party"]

    if len(party) >= 10:
        error("モンスターが一杯です！", jump="my_page")

    item = Medal_lsit[m_name]
    price = item["price"]
    currency = "medal" if item["type"] == "メダル" else "money"

    if user[currency] < price:
        error(f"{item['type']}が足りません！", jump="my_page")

    new_mob = monster_select(m_name)
    party.append(new_mob)
    for i, pt in enumerate(party, 1):
        pt["no"] = i

    user[currency] -= price

    user_all["user"] = user
    user_all["party"] = party

    save_user_all(user_all, user_name)

    success(f"【{m_name}】が仲間に加わりました", jump="medal_shop")
