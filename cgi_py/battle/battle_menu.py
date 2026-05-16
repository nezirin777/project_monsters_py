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

    # =====================================================
    # 敵リスト
    # =====================================================

    if special_flag:
        valid_enemies = [{"index": 1, "name2": battle["teki"][1].get("name2", "不明")}]
    else:
        valid_enemies = [
            {"index": i, "name2": mon.get("name2", "不明")}
            for i, mon in enumerate(battle["teki"][1:], 1)
            if str(mon.get("hp", 0)) != "0"
        ]

    # =====================================================
    # 仲間リスト
    # =====================================================
    valid_party = [
        {"index": i, "name": pt.get("name", "不明")}
        for i, pt in enumerate(battle.get("party", []))
    ]

    # =====================================================
    # 特技構築
    # =====================================================

    Tokugi_dat = open_tokugi_dat()

    for pt in battle.get("party", []):

        last_hit = pt.get("last_hit", "攻撃")
        last_target = pt.get("last_target", 1)
        last_toku = pt.get("last_toku", "通常攻撃")
        last_nakama = pt.get("last_nakama", 0)
        last_ktoku = pt.get("last_ktoku", "0")

        # -------------------------
        # 行動
        # -------------------------

        pt["hit_options"] = [
            {
                "value": "攻撃",
                "label": "攻撃",
                "selected": last_hit == "攻撃",
            }
        ]

        if not special_flag:
            pt["hit_options"].append(
                {
                    "value": "防御",
                    "label": "防御する",
                    "selected": last_hit == "防御",
                }
            )
            pt["hit_options"].append(
                {
                    "value": "回復",
                    "label": "回復魔法使用",
                    "selected": last_hit == "回復",
                }
            )

        # -------------------------
        # 敵ターゲット
        # -------------------------
        pt["target_options"] = []
        for enemy in valid_enemies:
            pt["target_options"].append(
                {
                    "value": enemy["index"],
                    "label": enemy["name2"],
                    "selected": enemy["index"] == last_target,
                }
            )

        # -------------------------
        # 攻撃特技
        # -------------------------
        pt["attack_skills"] = []

        # 特殊戦闘
        if special_flag:
            pt["attack_skills"].append(
                {
                    "name": "通常攻撃",
                    "mp": 0,
                    "selected": True,
                }
            )

        else:
            for name, toku in Tokugi_dat.items():
                if not waza.get(name, {}).get("get"):
                    continue
                if toku.get("type") != 1:
                    continue

                skill_mp = toku.get("mp", 0)

                # MP不足なら選択解除
                is_selected = name == last_toku and pt.get("mp", 0) >= skill_mp

                pt["attack_skills"].append(
                    {
                        "name": name,
                        "mp": skill_mp,
                        "selected": is_selected,
                    }
                )

        # -------------------------
        # 回復対象
        # -------------------------
        pt["nakama_options"] = []
        for member in valid_party:
            pt["nakama_options"].append(
                {
                    "value": member["index"],
                    "label": member["name"],
                    "selected": member["index"] == last_nakama,
                }
            )

        # -------------------------
        # 回復特技
        # -------------------------
        pt["heal_skills"] = [
            {
                "name": "0",
                "label": "使用しない",
                "mp": 0,
                "selected": last_ktoku == "0",
            }
        ]

        for name, toku in Tokugi_dat.items():
            if not waza.get(name, {}).get("get"):
                continue
            if toku.get("type") == 1:
                continue
            pt["heal_skills"].append(
                {
                    "name": name,
                    "label": name,
                    "mp": toku.get("mp", 0),
                    "selected": name == last_ktoku,
                }
            )

    # 数値整形
    party_data = battle.get("party", [])
    for pt in party_data:
        pt["hp"] = slim_number_with_cookie(pt.get("hp", 0))
        pt["mhp"] = slim_number_with_cookie(pt.get("mhp", 0))
        pt["mp"] = slim_number_with_cookie(pt.get("mp", 0))
        pt["mmp"] = slim_number_with_cookie(pt.get("mmp", 0))

    return {
        "party": party_data,
        "special_flag": special_flag,
        "token": token,
    }
