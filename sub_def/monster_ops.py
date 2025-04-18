# monster_ops.py
import sys
import random
from functools import lru_cache
from typing import Dict, Optional

import conf

from .utils import error
from .file_ops import *

sys.stdout.reconfigure(encoding="utf-8")
sys.stdin.reconfigure(encoding="utf-8")

Conf = conf.Conf


@lru_cache(maxsize=1)
def _cached_open_monster_dat() -> dict:
    return open_monster_dat()


@lru_cache(maxsize=1)
def _cached_open_seikaku_dat() -> dict:
    return open_seikaku_dat()


@lru_cache(maxsize=1)
def _cached_open_monster_boss_dat() -> dict:
    return open_monster_boss_dat()


SEX_OPTIONS = Conf["sex"]
SEIKAKU_KEYS = list(_cached_open_seikaku_dat().keys())

BASE_STAT = lambda stat, mon, haigou_hosei, floor_hosei: int(
    (mon.get(stat, 0) + haigou_hosei) * floor_hosei
)


# ==========#
# 特技取得  #
# ==========#
def waza_get(target: str, user_name: str = "") -> Optional[Dict]:
    waza = open_waza(user_name)
    if target not in waza:
        error(f"特技 {target} がデータに見つかりません。", 99)
        return None
    waza[target]["get"] = 1
    save_waza(waza, user_name)


# ==========#
# 図鑑登録  #
# ==========#
def zukan_get(target: str, user_name: str = "") -> None:
    try:
        # ユーザー情報と図鑑データを取得
        user = open_user(user_name)
        zukan = open_zukan(user_name)

        if target not in zukan:
            error(f"ターゲット {target} が図鑑に見つかりません。", 99)
            return None

        zukan[target]["get"] = 1
        get_count = sum(1 for val in zukan.values() if val.get("get", 0) == 1)
        total_count = len(zukan)

        # 進捗率を計算
        progress_percentage = (get_count / total_count) * 100
        user["getm"] = f"{get_count}／{total_count}匹 ({progress_percentage:.2f}％)"

        # 更新された報を保存
        save_zukan(zukan, user_name)
        save_user(user, user_name)
    except Exception as e:
        error(f"図鑑の更新中にエラーが発生しました: {e}", 99)
        return None


# ==================#
# モンスターセレクト#
# ==================#
# 配合、交換所等GET 基礎ステ + 補正(配合回数/2)
def select_base_mon(
    mon: dict,
    name: str = "",
    haigou_hosei: float = 0,
    floor_hosei: float = 1,
    exp_modifier: float = 1,
) -> dict:
    """
    モンスターの基本情報を生成する共通関数。

    Parameters:
    mon (dict): モンスターの元データ。
    haigou_hosei (float): ステータス補正値。
    exp_modifier (float): 経験値や報酬の倍率調整。

    Returns:
    dict: 生成されたモンスターの辞書。
    """
    return {
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
    Mons = _cached_open_monster_dat()
    mon = Mons.get(target)

    if not mon:
        error(f"モンスター {target} が見つかりません。", 99)
        return None

    new_mob = select_base_mon(
        mon,
        name=target,
        haigou_hosei=hosei,
    )
    new_mob.update(
        {
            "lv": 2,
            "mlv": 10,
            "hai": 0,
            "exp": 0,
            "n_exp": int(Conf["nextup"]),
        }
    )

    if get:
        waza_get(mon.pop("waza", []), user_name)
        zukan_get(new_mob["name"], user_name)

    return new_mob


def battle_monster_select(
    target: str, hosei: float, in_floor: float, is_boss: bool = False
) -> dict:
    """バトル用のモンスター（通常またはボス）を生成
    Parameters:
        target (str): モンスターの名前
        hosei (float): ステータス補正値
        in_floor (float): フロアによる補正値
        is_boss (bool): ボスモンスターかどうか（デフォルトはFalse）
    Returns:
        dict: 生成されたモンスター情報
    """
    Mons = _cached_open_monster_boss_dat() if is_boss else _cached_open_monster_dat()

    mon = Mons.get(target)
    if not mon:
        error(f"{'ボス' if is_boss else ''}モンスター {target} が見つかりません。", 99)
        return None

    new_mob = select_base_mon(
        mon,
        name=target,
        floor_hosei=hosei,
        exp_modifier=in_floor,
    )
    new_mob["name2"] = target
    return new_mob


# 置き換え
def battle_mob_select(target: str, hosei: float, in_floor: float) -> dict:
    return battle_monster_select(target, hosei, in_floor, is_boss=False)


def battle_boss_select(target: str, hosei: float, in_floor: float) -> dict:
    return battle_monster_select(target, hosei, in_floor, is_boss=True)
