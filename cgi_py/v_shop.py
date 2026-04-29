# 100vips = 50メダル,10vips = 5メダル,1vips = 0.5メダル
from sub_def.file_ops import open_vips_shop_dat, open_user_all, save_user_all
from sub_def.utils import print_html, get_and_clear_flash, error, success
from sub_def.monster_ops import monster_select
import conf

Conf = conf.Conf


def add_monster_to_party(party, monster_name, m_name):
    """モンスターをパーティに追加"""
    if len(party) >= 10:
        error("モンスターが一杯です！", jump="my_page")

    # 特殊モンスターの初期値設定
    special_settings = {
        "スライム+100": {"hai": 100, "mlv": 100},
        "スライム+1000": {"hai": 1000, "mlv": 1000},
    }

    new_mob = monster_select(monster_name)
    settings = special_settings.get(m_name, {})
    new_mob.update(settings)
    new_mob["lv"] = 1

    party.append(new_mob)
    for i, pt in enumerate(party, 1):
        pt["no"] = i


def v_shop_ok(FORM):
    if not (FORM.get("m_name")):
        error("対象が選択されていません。", jump="v_shop")

    m_name = FORM["m_name"]
    user_name = FORM["s"]["in_name"]

    user_all = open_user_all(user_name)
    user = user_all.get("user", {})
    party = user_all.get("party", [])
    vips = user_all.get("vips", {})

    vshop_list = open_vips_shop_dat()

    # 購入対象のデータ取得
    item = vshop_list[m_name]
    Aname = item["b_name"]
    price = item["price"] + item["price"] * vips.get(m_name, 0)

    # 資金のチェックと引き落とし
    currency = "medal" if item["type"] == "メダル" else "money"
    if user[currency] < price:
        error(f"{item['type']}が足りません！", jump="my_page")
        return
    user[currency] -= price

    # パーティに追加
    add_monster_to_party(party, Aname, m_name)

    # 購入回数更新
    vips[m_name] = vips.get(m_name, 0) + 1

    # 各データ保存
    user_all["user"] = user
    user_all["party"] = party
    user_all["vips"] = vips
    save_user_all(user_all, user_name)

    success(f"【{Aname}】が仲間に加わりました！", jump="v_shop")
