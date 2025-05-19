# 100vips = 50メダル,10vips = 5メダル,1vips = 0.5メダル
import sub_def
import conf

Conf = conf.Conf


def add_monster_to_party(party, monster_name, m_name):
    """モンスターをパーティに追加"""
    if len(party) >= 10:
        sub_def.error("モンスターが一杯です！")

    # 特殊モンスターの初期値設定
    special_settings = {
        "スライム+100": {"hai": 100, "mlv": 100},
        "スライム+1000": {"hai": 1000, "mlv": 1000},
    }

    new_mob = sub_def.monster_select(monster_name)
    settings = special_settings.get(m_name, {})
    new_mob.update(settings)
    new_mob["lv"] = 1

    party.append(new_mob)
    for i, pt in enumerate(party, 1):
        pt["no"] = i


def v_shop_ok(FORM):
    token = FORM["token"]
    if not (FORM.get("m_name")):
        sub_def.error("対象が選択されていません。")

    m_name = FORM["m_name"]
    vshop_list = sub_def.open_vips_shop_dat()
    user = sub_def.open_user()
    party = sub_def.open_party()
    vips = sub_def.open_vips()

    # 購入対象のデータ取得
    item = vshop_list[m_name]
    Aname = item["b_name"]
    price = item["price"] + item["price"] * vips.get(m_name, 0)

    # 資金のチェックと引き落とし
    currency = "medal" if item["type"] == "メダル" else "money"
    if user[currency] < price:
        sub_def.error(f"{item['type']}が足りません！")
        return
    user[currency] -= price

    # パーティに追加
    add_monster_to_party(party, Aname, m_name)

    # 購入回数更新
    vips[m_name] = vips.get(m_name, 0) + 1

    # 各データ保存
    sub_def.save_user(user)
    sub_def.save_party(party)
    sub_def.save_vips(vips)

    html = f"""
        <form action="{{ Conf.cgi_url }}" method="post">
            <input type="hidden" name="mode" value="v_shop">
            <input type="hidden" name="token" value="{token}">
            <button type="submit">交換所に戻る</button>
        </form>
    """

    sub_def.print_result(
        f"""<img src="{Conf["imgpath"]}/{Aname}.gif"><span>{m_name}</span>が仲間に加わりました""",
        html,
        token,
    )
