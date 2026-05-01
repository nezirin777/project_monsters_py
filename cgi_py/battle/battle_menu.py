# battle_menu.py 戦闘メニュー作成


from sub_def.file_ops import open_battle, open_user_all, open_tokugi_dat
from sub_def.utils import slim_number_with_cookie, error

import conf

Conf = conf.Conf


def battle_menu(FORM, special):
    session = FORM.get("s", {})
    user_name = session.get("in_name")
    token = session.get("token")

    if not user_name:
        error("ユーザー名が取得できませんでした。", "top")

    special_flag = special in ("わたぼう", "スライム")

    battle = open_battle(user_name)
    all_data = open_user_all(user_name)
    waza = all_data.get("waza", {})

    # 敵リストの構築
    if special_flag:
        valid_enemies = [{"index": 1, "name2": battle["teki"][1].get("name2", "不明")}]
    else:
        valid_enemies = [
            {"index": i, "name2": mon.get("name2", "不明")}
            for i, mon in enumerate(battle["teki"][1:], 1)
            if str(mon.get("hp", 0)) != "0"
        ]

    # スキルと仲間リストの構築
    attack_skills = []
    heal_skills = []
    valid_party = []

    if special_flag:
        attack_skills.append({"name": "通常攻撃", "mp": 0, "selected": True})
    else:
        Tokugi_dat = open_tokugi_dat()

        for name, toku in Tokugi_dat.items():
            if waza.get(name, {}).get("get"):
                if toku.get("type") == 1:
                    attack_skills.append({"name": name, "mp": toku.get("mp", 0)})
                else:
                    heal_skills.append({"name": name, "mp": toku.get("mp", 0)})

        valid_party = [
            {"index": i, "name": pt.get("name", "不明")}
            for i, pt in enumerate(battle.get("party", []))
        ]

    return {
        "party": slim_number_with_cookie(battle.get("party", [])),
        "valid_enemies": valid_enemies,
        "attack_skills": attack_skills,
        "heal_skills": heal_skills,
        "valid_party": valid_party,
        "special_flag": special_flag,
        "token": token,
    }
