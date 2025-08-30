from jinja2 import Environment, FileSystemLoader
import sub_def
import conf

Conf = conf.Conf


def battle_menu(FORM, special):
    token = FORM["token"]

    if special in ("わたぼう", "スライム"):
        special = True
    else:
        special = False

    # 各データの取得
    battle = sub_def.open_battle()
    Tokugi_dat = sub_def.open_tokugi_dat() if not special else None
    waza = sub_def.open_waza() if not special else None

    # 選択オプション用のHTML生成
    enemy_options = (
        f"""<option value=1>{battle["teki"][1]["name2"]}</option>"""
        if special
        else "".join(
            f"""<option value={i}>{mon["name2"]}</option>"""
            for i, mon in enumerate(battle["teki"][1:], 1)
            if mon["hp"] != 0
        )
    )

    special_skill_options = (
        f"""<option value="通常攻撃" SELECTED>通常攻撃</option>"""
        if special
        else "".join(
            f"""<option value={name}>{name} ({toku["mp"]} MP)</option>"""
            for name, toku in Tokugi_dat.items()
            if waza[name]["get"] and waza[name]["type"] == 1
        )
    )

    healing_skill_options = (
        ""
        if special
        else "".join(
            f"""<option value={name}>{name} ({toku["mp"]} MP)</option>"""
            for name, toku in Tokugi_dat.items()
            if waza[name]["get"] and waza[name]["type"] != 1
        )
    )

    party_member_options = (
        ""
        if special
        else "".join(
            f"""<option value={i}>{pt["name"]}</option>"""
            for i, pt in enumerate(battle["party"])
        )
    )

    # テンプレートエンジンの初期化
    env = Environment(loader=FileSystemLoader("./templates"))
    template = env.get_template("battle_menu_tmp.html")

    # HTML生成
    return template.render(
        party=sub_def.slim_number_with_cookie(battle["party"]),
        imgpath=Conf["imgpath"],
        enemy_options=enemy_options,
        special_skill_options=special_skill_options,
        healing_skill_options=healing_skill_options,
        party_member_options=party_member_options,
        special=int(special),
        token=token,
        Conf=Conf,
    )
