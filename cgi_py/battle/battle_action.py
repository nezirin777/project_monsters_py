# battle_action.py - 戦闘各コマンド処理

import random
from sub_def.utils import slim_number_with_cookie


def kaifuku(target, kairyou):
    """回復ロジックとログ生成"""
    if target.get("hp", 0) == 0:
        return f"""<span class="sky_blue">{target.get("name", "味方")}</span>は既に力尽きていた"""

    target["hp"] = min(
        target.get("hp", 0) + int(target.get("mhp", 1) * kairyou), target.get("mhp", 1)
    )
    log2 = int(kairyou * 100)
    return f"""<span class="sky_blue">{target.get("name", "味方")}</span>のHPが約{log2}%回復した"""


def sosei(target, kairyou, luk):
    """蘇生ロジックとログ生成"""
    if target.get("hp", 0) != 0:
        return f"""<span class="sky_blue">{target.get("name", "味方")}</span>は生きています"""

    if luk == 0:
        return f"""<span class="sky_blue">{target.get("name", "味方")}</span>は生きかえらなかった"""

    target["hp"] = int(target.get("mhp", 1) * kairyou)
    target["休み"] = 1
    return (
        f"""<span class="sky_blue">{target.get("name", "味方")}</span>は生きかえった"""
    )


def calculate_damage(attacker, defender, atk_modifier=1.0, def_modifier=1.0):
    """ダメージ計算ロジック"""
    defe = defender.get("def", 0) * (
        2 if defender.get("bt", {}).get("hit", "") == "防御" else 1
    )

    atk_val = (
        attacker.get("atk", 0) * atk_modifier * random.choice([1.0, 1.1, 1.2, 1.3])
    )
    def_val = defe * def_modifier * random.choice([0.9, 1.0, 1.1, 1.2])

    dmg = max(0, int(atk_val - def_val))
    defender["hp"] = max(0, defender.get("hp", 0) - dmg)

    return dmg


def create_action_log(actor, target, txt, turn):
    """HTMLではなく、テンプレートに渡すための純粋なデータ(辞書)を作成する"""
    return {
        "turn": turn,
        "actor": slim_number_with_cookie(actor),
        "target": slim_number_with_cookie(target) if target else None,
        "text": txt,
    }


#############################################################################
def teki_action(actor, battle, special, in_floor, turn, Conf):

    lan = []

    if battle["party"][0].get("hp", 0) > 0:
        lan = [0]
    elif len(battle["party"]) > 1 and battle["party"][1].get("hp", 0) > 0:
        lan = [1]
    elif len(battle["party"]) > 2 and battle["party"][2].get("hp", 0) > 0:
        lan = [2]

    if in_floor > 500 or special == "異世界":
        lan = []
        if battle["party"][0].get("hp", 0) > 0:
            lan += [0] * 6
        if len(battle["party"]) > 1 and battle["party"][1].get("hp", 0) > 0:
            lan += [1] * 3
        if len(battle["party"]) > 2 and battle["party"][2].get("hp", 0) > 0:
            lan += [2]

    if not lan:
        return battle, None

    target_idx = random.choice(lan)
    if special in ("わたぼう", "スライム"):
        target_idx = 0

    target = battle["party"][target_idx]
    dmg = calculate_damage(actor, target)
    dmg2 = slim_number_with_cookie(dmg)

    if dmg == 0:
        txt = f"""<span class="sky_blue">{target.get("name")}</span>は<span class="red">{actor.get("name")}</span>の攻撃をかわした！"""
    else:
        txt = f"""<span class="red">{actor.get("name")}</span>は<span class="sky_blue">{target.get("name")}</span>に<span class="red">{dmg2}</span>ポイントのダメージを与えた！"""

    # 文字列の結合ではなく、辞書を返す
    log_dict = create_action_log(actor, target, txt, turn)
    return battle, log_dict


#################################################################################################
def mikata_action(actor, battle, Tokugi_dat, Seikaku_dat, turn, Conf):
    """味方の行動処理（戻り値として、battle辞書とログHTMLを返す）"""

    def mikata_atk(txt_prefix, zyumon, target, kaisin):
        if actor.get("mp", 0) < zyumon.get("mp", 0):
            return (
                txt_prefix
                + f"""<span class="red">{zyumon.get("name", "技")}</span>を唱えようとしたがMPが足りなかった！"""
            )

        actor["mp"] -= int(zyumon.get("mp", 0))

        if target.get("hp", 0) == 0:
            return (
                txt_prefix
                + f"""<span class="red">{target.get("name", "敵")}</span>に攻撃しようとしたが既に力尽きていた！"""
            )

        dmg = calculate_damage(actor, target, zyumon.get("damage", 1) * kaisin)
        dmg2 = slim_number_with_cookie(dmg)

        if kaisin == 2:
            txt_prefix += "会心の一撃！<br>"

        if dmg == 0:
            txt_prefix += f"""しかし<span class="red">{target.get("name", "敵")}</span>にダメージを与えることができなかった！"""
        else:
            txt_prefix += f"""<span class="yellow">{zyumon.get("name", "技")}</span>を繰り出し<br><span class="red">{target.get("name", "敵")}</span>に<span class="red">{dmg2}</span>ポイントのダメージを与えた！"""

            if target.get("hp", 0) == 0:
                txt_prefix += f"""<br><span class="red">{target.get("name", "敵")}</span>は倒れた"""

                # 倒した敵の情報を戦利品プール（teki[0]）に加算
                battle["teki"][0]["name"] = target.get("name", "")
                battle["teki"][0]["sex"] = target.get("sex", "？")
                battle["teki"][0]["exp"] += target.get("exp", 0)
                battle["teki"][0]["money"] += target.get("money", 0)
                battle["teki"][0]["down"] += 1

        return txt_prefix

    def mikata_kaifuku(txt_prefix, zyumon, nakama_idx):
        if actor.get("mp", 0) < zyumon.get("mp", 0):
            return (
                txt_prefix
                + f"""<span class="red">{zyumon.get("name", "魔法")}</span>を唱えようとしたがMPが足りなかった！"""
            )

        actor["mp"] -= int(zyumon.get("mp", 0))
        target_ally = battle["party"][nakama_idx]

        if zyumon.get("type") == 2:
            m_log = kaifuku(target_ally, zyumon.get("damage", 0))
        else:
            luk = random.randint(0, 1) if zyumon.get("name") == "ザオラル" else 1
            m_log = sosei(target_ally, zyumon.get("damage", 0), luk)

        return (
            txt_prefix
            + f"""<span class="red">{zyumon.get("name", "魔法")}</span>を唱えた<br>{m_log}"""
        )

    bt = actor.get("bt", {})
    txt = f"""<span class="sky_blue">{actor.get("name", "味方")}</span>は"""

    # 性格判定による会心・サボり処理
    kaisin = 1
    if random.randint(0, 3) == 0:
        s = Seikaku_dat.get(actor.get("sei", ""), {}).get("行動", 1)
        if s == 2:
            kaisin = 2
        elif s == 0:
            txt += "命令を聞かずに踊っている～♪"
            return battle, create_action_log(actor, None, txt, turn)

    # コマンドに応じた処理
    target_obj = None
    if bt.get("hit") == "攻撃":
        toku_name = bt.get("toku", "通常攻撃")
        zyumon = {
            "name": toku_name,
            **Tokugi_dat.get(toku_name, {"mp": 0, "damage": 1, "type": 1}),
        }
        target_idx = max(1, min(bt.get("target", 1), len(battle["teki"]) - 1))
        target_obj = battle["teki"][target_idx]
        txt = mikata_atk(txt, zyumon, target_obj, kaisin)

    elif bt.get("hit") == "回復" and bt.get("ktoku", "0") != "0":
        toku_name = bt.get("ktoku")
        zyumon = {
            "name": toku_name,
            **Tokugi_dat.get(toku_name, {"mp": 0, "damage": 0.5, "type": 2}),
        }
        nakama_idx = max(0, min(bt.get("nakama", 0), len(battle["party"]) - 1))
        txt = mikata_kaifuku(txt, zyumon, nakama_idx)

    elif bt.get("hit") == "防御":
        txt += "防御している"
    else:
        txt += "使用する魔法が選択されなかった！<br>"

    log_dict = create_action_log(actor, target_obj, txt, turn)
    return battle, log_dict
