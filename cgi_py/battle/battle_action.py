# battle_action.py 戦闘各コマンド処理

import random

from cgi_py.battle.battle_manager import BattleManager
from sub_def.utils import slim_number_with_cookie


def kaifuku(target: dict, kairyou: float) -> dict:
    """
    HP回復ロジック。
    対象がすでに戦闘不能（HP=0）の場合は回復せず失敗を返す。
    """
    if target.get("hp", 0) == 0:
        return {"type": "kaifuku", "success": False, "reason": "dead"}

    old_hp = target.get("hp", 0)
    heal_amount = int(target.get("mhp", 1) * kairyou)
    target["hp"] = min(old_hp + heal_amount, target.get("mhp", 1))

    return {"type": "kaifuku", "success": True, "heal_percent": int(kairyou * 100)}


def sosei(target: dict, kairyou: float, luk: int) -> dict:
    """
    蘇生ロジック。
    - 対象が生きていれば何もしない（alive）
    - luk=0 は蘇生失敗（ザオラルが外れた等）
    - 成功時は HP を部分回復し、蘇生直後のターンを行動不能にする
    """
    if target.get("hp", 0) != 0:
        return {"type": "sosei", "success": False, "reason": "alive"}

    if luk == 0:
        return {"type": "sosei", "success": False, "reason": "failed"}

    target["hp"] = int(target.get("mhp", 1) * kairyou)
    # 蘇生直後のターンは行動不能にする（battle_fight.py のクリーンアップで除去される）
    target["休み"] = 1
    return {"type": "sosei", "success": True}


def calculate_damage(
    attacker: dict,
    defender: dict,
    atk_modifier: float = 1.0,
    def_modifier: float = 1.0,
) -> int:
    """
    ダメージ計算ロジック。defender の hp を直接書き換える。

    防御中（bt.hit == "防御"）の相手は守備力が2倍扱いになる。
    atk / def にランダム係数を乗算して毎ターンブレを持たせる。
    """
    # 防御行動中は守備力を2倍に扱う
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


def teki_action(actor: dict, bm: BattleManager) -> None:
    """敵の行動処理"""
    party = bm.battle["party"]

    # 基本ターゲットプール: 先頭から順に最初の生存メンバーだけを対象にする
    lan: list[int] = []
    if party[0].get("hp", 0) > 0:
        lan = [0]
    elif len(party) > 1 and party[1].get("hp", 0) > 0:
        lan = [1]
    elif len(party) > 2 and party[2].get("hp", 0) > 0:
        lan = [2]

    # 大不評なので一旦除外。
    # if bm.in_floor > 500 or bm.special == "異世界":
    #    # 深層・異世界では先頭を重点的に狙う重み付き抽選に切り替える。
    #    # 同じインデックスを複数詰めることで確率を操作する（先頭:6, 2番手:3, 3番手:1）
    #    lan = []
    #    if party[0].get("hp", 0) > 0:
    #        lan += [0] * 6
    #    if len(party) > 1 and party[1].get("hp", 0) > 0:
    #        lan += [1] * 3
    #    if len(party) > 2 and party[2].get("hp", 0) > 0:
    #        lan += [2]

    # 全員HP0（全滅済み）なら行動しない
    if not lan:
        return

    # わたぼう・スライム戦は常に先頭(index=0)を対象にする
    target_idx = 0 if bm.special in ("わたぼう", "スライム") else random.choice(lan)
    target = party[target_idx]

    dmg = calculate_damage(actor, target)

    event = {
        "is_enemy": True,
        "actor_name": actor.get("name"),
        "target_name": target.get("name"),
        "damage": slim_number_with_cookie(dmg),
        "is_miss": dmg == 0,
        "is_dead": target.get("hp", 0) == 0,
    }

    bm.log_action(actor, target, event)


# =========================================================


def mikata_action(actor: dict, bm: BattleManager) -> None:
    """味方の行動処理"""
    bt = actor.get("bt", {})

    # テンプレートへ渡すイベント辞書のベース（全フィールドを初期化しておく）
    event: dict = {
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

    # 性格データを1回だけ取得する
    sei_data = bm.seikaku_dat.get(actor.get("sei", ""), {})
    # 行動タイプ: 0=サボりやすい / 1=普通 / 2=会心が出やすい
    action_type: int = sei_data.get("行動", 1)

    # 1/4 の確率でサボり判定を行う。action_type が 0 のときのみサボる
    if random.randint(0, 3) == 0:
        if action_type == 0:
            event["action_type"] = "sabori"
            bm.log_action(actor, None, event)
            return

    if bt.get("hit") == "攻撃":
        event["action_type"] = "attack"
        toku_name = bt.get("toku", "通常攻撃")
        # 特技データをマスターから取得。未登録の特技名が来た場合は通常攻撃相当のデフォルトを使う
        zyumon = {
            "name": toku_name,
            **bm.tokugi_dat.get(toku_name, {"mp": 0, "damage": 1, "type": 1}),
        }
        event["skill_name"] = zyumon["name"]

        # フォームからの target インデックスを teki の有効範囲にクランプする
        target_idx = max(1, min(bt.get("target", 1), len(bm.battle["teki"]) - 1))
        target_obj = bm.battle["teki"][target_idx]
        event["target_name"] = target_obj.get("name")

        if actor.get("mp", 0) < zyumon.get("mp", 0):
            event["no_mp"] = True
        elif target_obj.get("hp", 0) == 0:
            # 選択した敵がすでに倒れている
            event["is_dead"] = True
            event["damage"] = 0
        else:
            actor["mp"] -= int(zyumon.get("mp", 0))

            # 会心の一撃判定: action_type が 2 の性格のみ 1/3 確率で発動しダメージ2倍
            if action_type == 2:
                if random.random() < 1 / 3:
                    event["is_critical"] = True
                    kaisin = 2
                else:
                    kaisin = 1
            else:
                kaisin = 1

            dmg = calculate_damage(actor, target_obj, zyumon.get("damage", 1) * kaisin)
            event["damage"] = slim_number_with_cookie(dmg)

            if dmg == 0:
                event["is_miss"] = True
            elif target_obj.get("hp", 0) == 0:
                # 敵撃破: センチネル(teki[0])に名前・経験値・所持金・撃破数を集計する
                event["is_dead"] = True
                bm.battle["teki"][0]["name"] = target_obj.get("name", "")
                bm.battle["teki"][0]["sex"] = target_obj.get("sex", "不明な性別")
                bm.battle["teki"][0]["exp"] += target_obj.get("exp", 0)
                bm.battle["teki"][0]["money"] += target_obj.get("money", 0)
                bm.battle["teki"][0]["down"] += 1

        bm.log_action(actor, target_obj, event)

    elif bt.get("hit") == "回復" and bt.get("ktoku", "0") != "0":
        event["action_type"] = "heal"
        toku_name = bt.get("ktoku")
        # 回復特技データをマスターから取得。未登録の場合は HP 回復相当のデフォルトを使う
        zyumon = {
            "name": toku_name,
            **bm.tokugi_dat.get(toku_name, {"mp": 0, "damage": 0.5, "type": 2}),
        }
        event["skill_name"] = zyumon["name"]

        # フォームからの nakama インデックスを party の有効範囲にクランプする
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
                # ザオラルは 1/2 確率で失敗。それ以外の蘇生呪文は必ず成功（luk=1）
                luk = random.randint(0, 1) if zyumon.get("name") == "ザオラル" else 1
                event["heal_data"] = sosei(target_ally, zyumon.get("damage", 0), luk)

        bm.log_action(actor, target_ally, event)

    elif bt.get("hit") == "防御":
        event["action_type"] = "defend"
        bm.log_action(actor, None, event)
    else:
        # 行動未選択または想定外の hit 値の場合は「なし」として記録する
        event["action_type"] = "none"
        bm.log_action(actor, None, event)
