# medal_shop.py -モンスター交換処理

from sub_def.file_ops import open_medal_shop_dat, open_user_all, save_user_all
from sub_def.monster_ops import monster_select
from sub_def.utils import error, success

import conf

Conf = conf.Conf


def medal_shop_ok(FORM):
    """メダル交換の処理を行う"""
    m_name = FORM.get("m_name")

    if not m_name:
        error("対象が選択されていません。", jump="medal_shop")

    session = FORM.get("s", {})
    user_name = session.get("in_name")

    user_all = open_user_all(user_name)
    user = user_all.get("user", {})
    party = user_all.get("party", [])

    Medal_list = open_medal_shop_dat()

    if len(party) >= 10:
        error("モンスターが一杯です！", jump="my_page")

    # 不正なm_name対策
    item = Medal_list.get(m_name)
    if not item:
        error("指定されたモンスターが存在しません。", jump="medal_shop")

    price = int(item.get("price", 0))
    currency = "medal" if item.get("type") == "メダル" else "money"

    if int(user.get(currency, 0)) < price:
        error(f"{item.get('type', '資金')}が足りません！", jump="my_page")

    new_mob = monster_select(m_name)
    party.append(new_mob)

    for i, pt in enumerate(party, 1):
        pt["no"] = i

    user[currency] = int(user.get(currency, 0)) - price

    user_all["user"] = user
    user_all["party"] = party

    save_user_all(user_all, user_name)

    success(f"【{m_name}】が仲間に加わりました", jump="medal_shop")
