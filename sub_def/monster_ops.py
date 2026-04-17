# monster_ops.py

import sys
import random
from typing import Dict, Optional

import conf

from .utils import error
from .file_ops import (
    open_monster_dat,
    open_monster_boss_dat,
    open_seikaku_dat,
    open_user_all,
    save_user_all,
)

sys.stdout.reconfigure(encoding="utf-8")

Conf = conf.Conf

SEX_OPTIONS = Conf["sex"]

BASE_STAT = lambda stat, mon, haigou_hosei, floor_hosei: int(
    (mon.get(stat, 0) + haigou_hosei) * floor_hosei
)


# ============#
# 特技・図鑑登録（統合版）
# ============#
def register_monster_progress(
    waza_target: str = None, zukan_target: str = None, user_name: str = ""
) -> dict:
    """
    特技取得と図鑑登録を1つの関数で処理。
    両方とも新規の場合に True を返す。
    戻り値: {"waza_new": bool, "zukan_new": bool}
    """
    result = {"waza_new": False, "zukan_new": False}

    all_data = open_user_all(user_name)
    user = all_data.setdefault("user", {})
    waza = all_data.setdefault("waza", {})
    zukan = all_data.setdefault("zukan", {})

    # --- 特技取得 ---
    if waza_target:
        if waza_target not in waza:
            error(f"特技 {waza_target} がデータに見つかりません。", 99)
        elif waza[waza_target].get("get", 0) == 0:
            waza[waza_target]["get"] = 1
            result["waza_new"] = True

    # --- 図鑑登録 ---
    if zukan_target:
        if zukan_target not in zukan:
            error(f"図鑑ターゲット {zukan_target} がデータに見つかりません。", 99)
        elif zukan[zukan_target].get("get", 0) == 0:
            zukan[zukan_target]["get"] = 1
            result["zukan_new"] = True

            # 図鑑進捗率を更新
            get_count = sum(1 for val in zukan.values() if val.get("get", 0) == 1)
            total_count = len(zukan)
            progress = (get_count / total_count) * 100
            user["getm"] = f"{get_count}／{total_count}匹 ({progress:.2f}％)"

    # 保存（変更があった場合のみ）
    if result["waza_new"] or result["zukan_new"]:
        all_data["user"] = user
        all_data["waza"] = waza
        all_data["zukan"] = zukan
        save_user_all(all_data, user_name)

    return result


# ==================#
# モンスターセレクト #
# ==================#
def create_monster_base(
    mon: dict,
    name: str = "",
    haigou_hosei: float = 0,
    floor_hosei: float = 1,
    exp_modifier: float = 1,
    additional_attrs: dict = None,
) -> dict:
    """
    モンスターの基本情報を生成する共通関数。

    Parameters:
    mon (dict): モンスターの元データ。
    haigou_hosei (float): ステータス補正値。
    exp_modifier (float): 経験値や報酬の倍率調整。
    """
    SEIKAKU_KEYS = list(open_seikaku_dat().keys())
    base = {
        "name": name,
        "hp": BASE_STAT("hp", mon, haigou_hosei, floor_hosei),
        "mhp": BASE_STAT("hp", mon, haigou_hosei, floor_hosei),
        "mp": BASE_STAT("mp", mon, haigou_hosei, floor_hosei),
        "mmp": BASE_STAT("mp", mon, haigou_hosei, floor_hosei),
        "atk": BASE_STAT("atk", mon, haigou_hosei, floor_hosei),
        "def": BASE_STAT("def", mon, haigou_hosei, floor_hosei),
        "agi": BASE_STAT("agi", mon, haigou_hosei, floor_hosei),
        "exp": int(mon.get("exp", 0) * exp_modifier),
        "money": int(mon.get("money", 0) * exp_modifier),
        "sex": random.choice(SEX_OPTIONS),
        "sei": random.choice(SEIKAKU_KEYS),
    }

    if additional_attrs:
        base.update(additional_attrs)
    return base


def monster_select(
    target: str, hosei: float = 0, get: int = 0, user_name: str = ""
) -> dict:
    """
    ユーザーが取得するモンスターを生成。

    Parameters:
    target (str): モンスターの名前。
    hosei (float): 補正値。
    get (int): 図鑑への登録フラグ。
    user_name (str): ユーザー名。

    Returns:
    dict: 新しいモンスターの情報。
    """
    Mons = open_monster_dat()
    mon = Mons.get(target)

    if not mon:
        error(f"モンスター {target} が見つかりません。", 99)
        return None

    new_mob = create_monster_base(
        mon,
        name=target,
        haigou_hosei=hosei,
        additional_attrs={
            "lv": 2,
            "mlv": 10,
            "hai": 0,
            "exp": 0,
            "n_exp": int(Conf["nextup"]),
            "waza": mon.get("waza", ""),
            "room": mon.get("room", ""),
        },
    )

    return new_mob


def battle_monster_select(
    target: str, hosei: float, in_floor: float, is_boss: bool = False
) -> dict:
    """
    バトル用のモンスター（通常またはボス）を生成

    Parameters:
        target (str): モンスターの名前
        hosei (float): ステータス補正値
        in_floor (float): フロアによる補正値
        is_boss (bool): ボスモンスターかどうか（デフォルトはFalse）

    Returns:
        dict: 生成されたモンスター情報
    """
    Mons = open_monster_boss_dat() if is_boss else open_monster_dat()

    mon = Mons.get(target)
    if not mon:
        error(f"{'ボス' if is_boss else ''}モンスター {target} が見つかりません。", 99)
        return None

    new_mob = create_monster_base(
        mon,
        name=target,
        floor_hosei=hosei,
        exp_modifier=in_floor,
    )
    new_mob["name2"] = target
    return new_mob


def battle_mob_select(target: str, hosei: float, in_floor: float) -> dict:
    return battle_monster_select(target, hosei, in_floor, is_boss=False)


def battle_boss_select(target: str, hosei: float, in_floor: float) -> dict:
    return battle_monster_select(target, hosei, in_floor, is_boss=True)
