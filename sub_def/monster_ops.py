# monster_ops.py

import random
from typing import Dict, Optional

import conf

from .utils import error
from .file_ops import (
    open_monster_dat,
    open_monster_boss_dat,
    open_seikaku_dat,
)

# sys.stdout.reconfigure はライブラリモジュールには不要。
# CGI エントリポイント（login.py / monster.py 等）で設定済みのため削除。

Conf = conf.Conf

SEX_OPTIONS: list[str] = Conf.get("sex", ["陰", "陽"])

# 性格キーはゲーム中に変わらないためモジュールロード時に 1 回だけ読み込む。
# create_monster_base が呼ばれるたびにファイル I/O が走るのを防ぐ。
_SEIKAKU_KEYS: list[str] = list(open_seikaku_dat().keys())


# =========================#
# 内部ユーティリティ       #
# =========================#
def _calc_base_stat(
    stat_name: str, mon: dict, haigou_hosei: float, floor_hosei: float
) -> int:
    """
    モンスターの基礎ステータスを計算して返す。

    (マスター値 + haigou_hosei) × floor_hosei で算出する。
    haigou_hosei はプレイヤーモンスターの配合ボーナス（敵は 0）。
    floor_hosei は出現階層に応じたステータス倍率（プレイヤーモンスターは 1）。
    """
    return int((mon.get(stat_name, 0) + haigou_hosei) * floor_hosei)


# ============================================#
# 特技・図鑑登録（統合版）                    #
# ============================================#
def register_monster_progress(
    waza_target: str | None = None,
    zukan_target: str | None = None,
    all_data: Dict = None,
) -> dict:
    """
    特技取得と図鑑登録を 1 つの関数でまとめて処理する。

    Args:
        waza_target : 取得を試みる特技名。None の場合はスキップ。
        zukan_target: 登録を試みるモンスター名。None の場合はスキップ。
        all_data    : open_user_all() で取得したユーザー全データ。必須。
                      保存は呼び出し元で行うこと。

    Returns:
        {"waza_new": bool, "zukan_new": bool}
        それぞれ今回新たに取得 / 登録された場合に True。
    """
    if all_data is None:
        # 型ヒントで Optional にしていないが念のため明示的にガードする
        error("register_monster_progress: all_data が指定されていません。", 99)

    result = {"waza_new": False, "zukan_new": False}

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

            # 取得率を再計算して user["getm"] を更新する
            get_count = sum(1 for val in zukan.values() if val.get("get", 0) == 1)
            total_count = len(zukan)
            progress = (get_count / total_count * 100) if total_count > 0 else 0.0
            user["getm"] = f"{get_count}／{total_count}匹 ({progress:.2f}％)"

    # 変更があった場合のみ all_data に書き戻す（呼び出し元で save すること）
    if result["waza_new"] or result["zukan_new"]:
        all_data["user"] = user
        all_data["waza"] = waza
        all_data["zukan"] = zukan

    return result


# =========================#
# モンスター生成 共通処理  #
# =========================#
def create_monster_base(
    mon: dict,
    name: str = "",
    haigou_hosei: float = 0,
    floor_hosei: float = 1,
    exp_modifier: float = 1,
    additional_attrs: Optional[dict] = None,
) -> dict:
    """
    モンスターの基本ステータス辞書を生成して返す共通関数。

    Args:
        mon            : マスターデータの 1 モンスター分の辞書。
        name           : モンスター名。
        haigou_hosei   : 配合ボーナス（加算値）。プレイヤーモンスター用。
        floor_hosei    : 階層倍率（乗算値）。敵モンスター用。
        exp_modifier   : 経験値・お金への倍率。
        additional_attrs: 生成後に上書きする追加属性。
    """
    base = {
        "name": name,
        "hp": _calc_base_stat("hp", mon, haigou_hosei, floor_hosei),
        "mhp": _calc_base_stat("hp", mon, haigou_hosei, floor_hosei),
        "mp": _calc_base_stat("mp", mon, haigou_hosei, floor_hosei),
        "mmp": _calc_base_stat("mp", mon, haigou_hosei, floor_hosei),
        "atk": _calc_base_stat("atk", mon, haigou_hosei, floor_hosei),
        "def": _calc_base_stat("def", mon, haigou_hosei, floor_hosei),
        "agi": _calc_base_stat("agi", mon, haigou_hosei, floor_hosei),
        "exp": int(mon.get("exp", 0) * exp_modifier),
        "money": int(mon.get("money", 0) * exp_modifier),
        "sex": random.choice(SEX_OPTIONS),
        "sei": random.choice(_SEIKAKU_KEYS),
    }

    if additional_attrs:
        base.update(additional_attrs)
    return base


# =========================#
# プレイヤーモンスター生成 #
# =========================#
def monster_select(target: str, hosei: float = 0) -> dict:
    """
    プレイヤーが取得するモンスターを生成して返す。

    Note:
        図鑑登録は呼び出し側で register_monster_progress() を使うこと。
    """
    Mons = open_monster_dat()
    mon = Mons.get(target)

    if not mon:
        error(f"モンスター {target} が見つかりません。", 99)
        raise RuntimeError("unreachable")  # error() → sys.exit() で到達しない

    return create_monster_base(
        mon,
        name=target,
        haigou_hosei=hosei,
        additional_attrs={
            "lv": 2,
            "mlv": 10,
            "hai": 0,
            "exp": 0,
            "n_exp": int(Conf["nextup"]),
        },
    )


# =========================#
# バトル用モンスター生成   #
# =========================#
def battle_monster_select(
    target: str, hosei: float, in_floor: float, is_boss: bool = False
) -> dict:
    """
    バトル用の敵モンスター（通常 or ボス）を生成して返す。

    Args:
        target  : モンスター名。
        hosei   : 階層に基づくステータス倍率（floor_hosei に渡す）。
        in_floor: 経験値・お金の倍率として使用する。
        is_boss : True の場合はボスデータから生成する。
    """
    Mons = open_monster_boss_dat() if is_boss else open_monster_dat()
    mon = Mons.get(target)

    if not mon:
        label = "ボス" if is_boss else ""
        error(f"{label}モンスター {target} が見つかりません。", 99)
        raise RuntimeError("unreachable")  # error() → sys.exit() で到達しない

    new_mob = create_monster_base(
        mon,
        name=target,
        floor_hosei=hosei,  # 敵は haigou_hosei=0（デフォルト）のまま
        exp_modifier=in_floor,  # in_floor を経験値・お金の倍率として使用
    )
    new_mob["name2"] = target
    return new_mob


def battle_mob_select(target: str, hosei: float, in_floor: float) -> dict:
    """通常モンスターのバトル用インスタンスを生成する"""
    return battle_monster_select(target, hosei, in_floor, is_boss=False)


def battle_boss_select(target: str, hosei: float, in_floor: float) -> dict:
    """ボスモンスターのバトル用インスタンスを生成する"""
    return battle_monster_select(target, hosei, in_floor, is_boss=True)
