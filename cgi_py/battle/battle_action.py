# ========#
# 戦闘用 #
# ========#
import random
import sub_def
import conf

Conf = conf.Conf


def pr(actor, target, txt):

    c = sub_def.get_cookie()
    turn = c["turn"]

    actor2 = sub_def.slim_number(actor)
    target2 = sub_def.slim_number(target)

    html = f"""
        <div class="battle_log_a">
            <div><img src="{Conf["imgpath"]}/{actor2["name"]}.gif"></div>
            <div class="sky_blue">{actor2["name"]}</div>
            <div>HP / MHP<br>{actor2["hp"]} / {actor2["mhp"]}</div>
            <div>MP / MMP<br>{actor2["mp"]} / {actor2["mmp"]}</div>
        </div>
    """
    if target:
        html += f"""
            <div class="battle_R">{turn}<span>R</span></div>
            <div class="battle_log_b">
                <div><img src="{Conf["imgpath"]}/{target2["name"]}.gif"></div>
                <div class="red">{target2["name"]}</div>
                <div>HP / MHP<br>{target2["hp"]} / {target2["mhp"]}</div>
                <div>MP / MMP<br>{target2["mp"]} / {target2["mmp"]}</div>
            </div>
    """

    html += f"""<div class="battle_log">{txt}</div>"""
    print(f"""<div class="battle_log_box">{html}</div>""")


def kaifuku(target, kairyou):
    if target["hp"] == 0:
        return f"""<span class="sky_blue">{target["name"]}</span>は既に力尽きていた"""

    target["hp"] = min(target["hp"] + int(target["mhp"] * kairyou), target["mhp"])
    log2 = kairyou * 100
    return f"""<span class="sky_blue">{target["name"]}</span>のHPが約{log2}%回復した"""


def sosei(target, kairyou, luk):
    if target["hp"] != 0:
        return f"""<span class="sky_blue">{target["name"]}</span>は生きています"""

    if luk == 0:
        return f"""<span class="sky_blue">{target["name"]}</span>は生きかえらなかった"""

    target["hp"] = int(target["mhp"] * kairyou)
    target["休み"] = 1
    return f"""<span class="sky_blue">{target["name"]}</span>は生きかえった"""


def calculate_damage(attacker, defender, atk_modifier=1, def_modifier=1):
    """攻撃ロジックを共通化"""
    defe = defender["def"] * (
        2 if defender.get("bt", {}).get("hit", "") == "防御" else 1
    )
    dmg = max(
        0,
        int(
            (attacker["atk"] * atk_modifier * random.choice([1.0, 1.1, 1.2, 1.3]))
            - (defe * def_modifier * random.choice([0.9, 1.0, 1.1, 1.2]))
        ),
    )
    defender["hp"] = max(0, defender["hp"] - dmg)
    return dmg


#############################################################################
def teki_action(actor, battle, special, in_floor):

    lan = []
    if battle["party"][0]["hp"] > 0:
        lan = [0]
    elif battle["party"][1:2]:
        if battle["party"][1]["hp"] > 0:
            lan = [1]
        elif battle["party"][2:3]:
            if battle["party"][2]["hp"] > 0:
                lan = [2]

    if in_floor > 500 or special == "異世界":
        lan = []
        if battle["party"][0]["hp"] > 0:
            lan += [0, 0, 0, 0, 0, 0]
        if battle["party"][1:2]:
            if battle["party"][1]["hp"] > 0:
                lan += [1, 1, 1]
        if battle["party"][2:3]:
            if battle["party"][2]["hp"] > 0:
                lan += [2]

    if not lan:
        return battle

    target = battle["party"][random.choice(lan)]
    if special in ("わたぼう", "スライム"):
        target = battle["party"][0]

    dmg = calculate_damage(actor, target)
    dmg2 = sub_def.slim_number(dmg)

    if dmg == 0:
        txt = f"""<span class="sky_blue">{target["name"]}</span>は<span class="red">{actor["name"]}</span>の攻撃をかわした！"""
    else:
        txt = f"""<span class="red">{actor["name"]}</span>は<span class="sky_blue">{target["name"]}</span>に<span class="red">{dmg2}</span>ポイントのダメージを与えた！"""

    pr(target, actor, txt)
    return battle


#################################################################################################
def mikata_action(actor, battle):

    def mikata_atk(txt):
        if actor["mp"] < zyumon["mp"]:
            return (
                txt
                + f"""<span class="red">{zyumon["name"]}</span>を唱えようとしたがMPが足りなかった！"""
            )
        actor["mp"] -= int(zyumon["mp"])
        if target.get("hp", 0) == 0:
            return (
                txt
                + f"""<span class="red">{target["name"]}</span>に攻撃しようとしたが既に力尽きていた！"""
            )

        dmg = calculate_damage(actor, target, zyumon["damage"] * kaisin)
        dmg2 = sub_def.slim_number(dmg)

        if kaisin == 2:
            txt += "会心の一撃！<br>"
        if dmg == 0:
            txt += f"""しかし<span class="red">{target["name"]}</span>にダメージを与えることができなかった！"""
        else:
            txt += f"""<span class="yellow">{zyumon["name"]}</span>を繰り出し<br><span class="red">{target["name"]}</span>に<span class="red">{dmg2}</span>ポイントのダメージを与えた！"""

            if target["hp"] == 0:
                txt += f"""<br><span class="red">{target["name"]}</span>は倒れた"""

                battle["teki"][0]["name"] = target["name"]  # 起き上がり対象に
                battle["teki"][0]["sex"] = target["sex"]
                battle["teki"][0]["exp"] += target["exp"]
                battle["teki"][0]["money"] += target["money"]
                battle["teki"][0]["down"] += 1

        return txt

    def mikata_kaifuku(txt):
        if actor["mp"] < zyumon["mp"]:
            return (
                txt
                + f"""<span class="red">{zyumon["name"]}</span>を唱えようとしたがMPが足りなかった！"""
            )
        actor["mp"] -= int(zyumon["mp"])
        if zyumon["type"] == 2:
            # (対象味方,回復量)
            m_log = kaifuku(battle["party"][bt["nakama"]], zyumon["damage"])
        else:
            luk = random.randint(0, 1) if (zyumon["name"] == "ザオラル") else 1
            # (対象味方,回復量,ザオラル判定)
            m_log = sosei(battle["party"][bt["nakama"]], zyumon["damage"], luk)

        return txt + f"""<span class="red">{zyumon["name"]}</span>を唱えた<br>{m_log}"""

    bt = actor["bt"]

    Tokugi_dat = sub_def.open_tokugi_dat()
    Seikaku_dat = sub_def.open_seikaku_dat()

    txt = f"""<span class="sky_blue">{actor["name"]}</span>は"""

    ### 性格判定 ###
    # 2 = 会心 ( "ねっけつかん","いのちしらず","いっぴきおおかみ","れいせいちんちゃく","きれもの","こうかつ","ちょとつもうしん")
    # 0 = さぼり ( "きまぐれ","あわてもの","ひねくれもの","がんこもの","ゆうじゅうふだん","うっかりもの","のんきもの","おひとよし","おくびょうもの","なまけもの","わがまま","うぬぼれや")
    # 1/4確率で会心もしくはさぼり=3/4で通常攻撃 kaisin=2→会心 kaisin=0→さぼり
    kaisin = 1
    if random.randint(0, 3) == 0:
        s = Seikaku_dat[actor["sei"]]["行動"]
        if s == 2:
            kaisin = 2
        elif s == 0:
            txt += "命令を聞かずに踊っている～♪"
            pr(actor, "", txt)
            return battle

    zyumon = {}
    if bt["hit"] == "攻撃":
        zyumon = {**{"name": bt["toku"]}, **Tokugi_dat[bt["toku"]]}
        target = battle["teki"][bt["target"]]
        txt = mikata_atk(txt)

    elif bt["hit"] == "回復" and bt["ktoku"] != "0":
        zyumon = {**{"name": bt["ktoku"]}, **Tokugi_dat[bt["ktoku"]]}
        target = ""
        txt = mikata_kaifuku(txt)

    elif bt["hit"] == "防御":
        zyumon["mp"] = 0
        target = ""
        txt += "防御している"

    if not zyumon:
        txt += "使用する魔法が選択されなかった！<br>"

    target = target if "target" in locals() else 0

    pr(actor, target, txt)
    return battle


#################################################################################################
