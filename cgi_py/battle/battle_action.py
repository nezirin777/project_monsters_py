# battle_action.py 戦闘各コマンド処理


import random
from sub_def.utils import slim_number_with_cookie


def kaifuku(target, kairyou):
    """回復ロジック（純粋なデータのみを返す）"""
    if target.get("hp", 0) == 0:
        return {"type": "kaifuku", "success": False, "reason": "dead"}

    old_hp = target.get("hp", 0)
    heal_amount = int(target.get("mhp", 1) * kairyou)
    target["hp"] = min(old_hp + heal_amount, target.get("mhp", 1))

    return {"type": "kaifuku", "success": True, "heal_percent": int(kairyou * 100)}


def sosei(target, kairyou, luk):
    """蘇生ロジック（純粋なデータのみを返す）"""
    if target.get("hp", 0) != 0:
        return {"type": "sosei", "success": False, "reason": "alive"}

    if luk == 0:
        return {"type": "sosei", "success": False, "reason": "failed"}

    target["hp"] = int(target.get("mhp", 1) * kairyou)
    target["休み"] = 1
    return {"type": "sosei", "success": True}


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


# =========================================================


def teki_action(actor, bm):
    """敵の行動処理"""
    lan = []
    party = bm.battle["party"]

    if party[0].get("hp", 0) > 0:
        lan = [0]
    elif len(party) > 1 and party[1].get("hp", 0) > 0:
        lan = [1]
    elif len(party) > 2 and party[2].get("hp", 0) > 0:
        lan = [2]

    if bm.in_floor > 500 or bm.special == "異世界":
        lan = []
        if party[0].get("hp", 0) > 0:
            lan += [0] * 6
        if len(party) > 1 and party[1].get("hp", 0) > 0:
            lan += [1] * 3
        if len(party) > 2 and party[2].get("hp", 0) > 0:
            lan += [2]

    if not lan:
        return

    target_idx = 0 if bm.special in ("わたぼう", "スライム") else random.choice(lan)
    target = party[target_idx]

    dmg = calculate_damage(actor, target)

    # テンプレートへ渡すイベント辞書
    event = {
        "is_enemy": True,
        "actor_name": actor.get("name"),
        "target_name": target.get("name"),
        "damage": slim_number_with_cookie(dmg),
        "is_miss": dmg == 0,
    }

    # bm.log_action の第3引数にそのまま辞書を渡す
    bm.log_action(actor, target, event)


# =========================================================
def mikata_action(actor, bm):
    """味方の行動処理"""
    bt = actor.get("bt", {})

    # テンプレートへ渡すイベント辞書のベース
    event = {
        "is_enemy": False,
        "actor_name": actor.get("name"),
        "target_name": None,
        "action_type": "none",
        "skill_name": "",
        "no_mp": False,
        "is_critical": False,
        "is_miss": False,
        "damage": 0,
        "is_dead": False,
        "heal_data": {},
    }

    # サボり判定
    if random.randint(0, 3) == 0:
        if bm.seikaku_dat.get(actor.get("sei", ""), {}).get("行動", 1) == 0:
            event["action_type"] = "sabori"
            bm.log_action(actor, None, event)
            return

    if bt.get("hit") == "攻撃":
        event["action_type"] = "attack"
        toku_name = bt.get("toku", "通常攻撃")
        zyumon = {
            "name": toku_name,
            **bm.tokugi_dat.get(toku_name, {"mp": 0, "damage": 1, "type": 1}),
        }
        event["skill_name"] = zyumon["name"]

        target_idx = max(1, min(bt.get("target", 1), len(bm.battle["teki"]) - 1))
        target_obj = bm.battle["teki"][target_idx]
        event["target_name"] = target_obj.get("name")

        if actor.get("mp", 0) < zyumon.get("mp", 0):
            event["no_mp"] = True
        elif target_obj.get("hp", 0) == 0:
            event["is_dead"] = True
            event["damage"] = 0
        else:
            actor["mp"] -= int(zyumon.get("mp", 0))
            kaisin = (
                2
                if bm.seikaku_dat.get(actor.get("sei", ""), {}).get("行動", 1) == 2
                else 1
            )
            if kaisin == 2:
                event["is_critical"] = True

            dmg = calculate_damage(actor, target_obj, zyumon.get("damage", 1) * kaisin)
            event["damage"] = slim_number_with_cookie(dmg)

            if dmg == 0:
                event["is_miss"] = True
            elif target_obj.get("hp", 0) == 0:
                event["is_dead"] = True
                bm.battle["teki"][0]["name"] = target_obj.get("name", "")
                bm.battle["teki"][0]["exp"] += target_obj.get("exp", 0)
                bm.battle["teki"][0]["money"] += target_obj.get("money", 0)
                bm.battle["teki"][0]["down"] += 1

        bm.log_action(actor, target_obj, event)

    elif bt.get("hit") == "回復" and bt.get("ktoku", "0") != "0":
        event["action_type"] = "heal"
        toku_name = bt.get("ktoku")
        zyumon = {
            "name": toku_name,
            **bm.tokugi_dat.get(toku_name, {"mp": 0, "damage": 0.5, "type": 2}),
        }
        event["skill_name"] = zyumon["name"]

        nakama_idx = max(0, min(bt.get("nakama", 0), len(bm.battle["party"]) - 1))
        target_ally = bm.battle["party"][nakama_idx]
        event["target_name"] = target_ally.get("name")

        if actor.get("mp", 0) < zyumon.get("mp", 0):
            event["no_mp"] = True
        else:
            actor["mp"] -= int(zyumon.get("mp", 0))
            if zyumon.get("type") == 2:
                event["heal_data"] = kaifuku(target_ally, zyumon.get("damage", 0))
            else:
                luk = random.randint(0, 1) if zyumon.get("name") == "ザオラル" else 1
                event["heal_data"] = sosei(target_ally, zyumon.get("damage", 0), luk)

        bm.log_action(actor, target_ally, event)

    elif bt.get("hit") == "防御":
        event["action_type"] = "defend"
        bm.log_action(actor, None, event)
    else:
        event["action_type"] = "none"
        bm.log_action(actor, None, event)
