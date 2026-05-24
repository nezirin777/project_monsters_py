# battle_sub.py 戦闘後処理

import random

import conf
from cgi_py.battle.battle_manager import BattleManager
from sub_def.file_ops import open_monster_dat
from sub_def.utils import slim_number_with_cookie

Conf = conf.Conf

# 経験値成長レートテーブル。レベル帯ごとに必要経験値の増加率が変わる。
# Lv_up() から分離してモジュール定数とすることで、
# レベルアップのたびに dict を再生成するコストを避ける
_GROWTH_RATES: dict = {
    "exp_rates": [
        (100, 1.15),
        (200, 1.0075),
        (300, 1.0045),
        (400, 1.0030),
        (500, 1.0025),
        (600, 1.0020),
        (700, 1.0017),
        (800, 1.0014),
        (900, 1.0012),
        (1000, 1.0010),
    ],
    "max_exp": 999999,
}


# LVup処理---------------------------------------------------------------------------
def Lv_up(pt0: dict) -> dict:
    """レベルアップ処理。ステータスを成長させて pt0 を返す"""
    pt0["lv"] = pt0.get("lv", 1) + 1
    pt0["exp"] = pt0.get("exp", 0) - int(pt0.get("n_exp", 0))

    # for/else: ループが break せずに完了した場合（全帯域を超えた場合）に x=1 を使う
    for max_lv, rate in _GROWTH_RATES["exp_rates"]:
        if pt0["lv"] <= max_lv:
            x = rate
            break
    else:
        x = 1

    pt0["n_exp"] = min(
        int(pt0.get("n_exp", 0) * x),
        int(pt0["lv"] * 1000),
        _GROWTH_RATES["max_exp"],
    )

    factors: dict[str, list[float]] = {
        "mhp": [0.8, 0.9, 1.0, 1.1, 1.2],
        "mmp": [0.7, 0.8, 0.9, 1.0, 1.1],
        "atk": [0.8, 0.9, 1.0, 1.1, 1.2],
        "def": [0.7, 0.8, 0.9, 1.0, 1.1],
        "agi": [0.7, 0.8, 0.9, 1.0, 1.1],
    }
    # 配合回数(hai)に比例したボーナス加算
    hosei: float = pt0.get("hai", 0) * 0.1

    def calculate_growth(
        base_value: int, random_factors: list[float], level: int
    ) -> int:
        """ランダム係数と現在レベルを使って成長量を計算する"""
        lan = random.choice(random_factors)
        return int(lan * base_value / level)

    for stat, rand_factors in factors.items():
        base_val = pt0.get(stat, 1)
        growth = calculate_growth(base_val, rand_factors, pt0["lv"])

        # HP/ATK: 低ステータス時に最低 +1 を保証する特別ルール
        # - 1のとき: 無条件で +1
        # - 2のとき: 50% 確率で +1
        # - 3以上: 通常の成長計算
        if stat in ("mhp", "atk"):
            if base_val == 1:
                pt0[stat] += 1
            elif base_val == 2:
                pt0[stat] += random.choice([0, 1])
            else:
                pt0[stat] += int(growth + hosei)
        else:
            pt0[stat] += int(growth + hosei)

    return pt0


def Lv_Max(pt0: dict) -> dict:
    """最大レベル到達時の処理。ステータスを配合回数ベースの固定値にリセットする"""
    hai = pt0.get("hai", 0)
    pt0["lv"] = pt0.get("mlv", 1)
    pt0["mhp"] = hai + 15
    pt0["mmp"] = hai + 14
    pt0["atk"] = hai + 25
    pt0["def"] = hai + 24
    pt0["agi"] = hai + 24
    pt0["exp"] = 0
    pt0["n_exp"] = 0
    # 現在 HP/MP は最大値を超えないよう調整する
    pt0["hp"] = min(pt0.get("hp", 0), pt0["mhp"])
    pt0["mp"] = min(pt0.get("mp", 0), pt0["mmp"])
    return pt0


# LVup出力処理---------------------------------------------------------------------------
def pr_Lv_up(pt0: dict, pt: dict) -> dict:
    """レベルアップログ用辞書を生成して返す（pt0: 上昇後, pt: 上昇前のスナップショット）"""
    return {
        "type": "lvup",
        "name": pt.get("name", ""),
        "old_lv": pt.get("lv", 1),
        "new_lv": pt0.get("lv", 2),
        "up_hp": slim_number_with_cookie(pt0.get("mhp", 0) - pt.get("mhp", 0)),
        "up_mp": slim_number_with_cookie(pt0.get("mmp", 0) - pt.get("mmp", 0)),
        "up_atk": slim_number_with_cookie(pt0.get("atk", 0) - pt.get("atk", 0)),
        "up_def": slim_number_with_cookie(pt0.get("def", 0) - pt.get("def", 0)),
        "up_agi": slim_number_with_cookie(pt0.get("agi", 0) - pt.get("agi", 0)),
        "is_max": False,
    }


def pr_Lv_Max(pt0: dict, pt: dict) -> dict:
    """最大レベル到達ログ用辞書を生成して返す（pt0: 上昇後, pt: 上昇前のスナップショット）"""
    return {
        "type": "lvup",
        "name": pt.get("name", ""),
        "old_lv": pt.get("lv", 1),
        "new_lv": pt0.get("mlv", 99),
        "is_max": True,
    }


# LVupチェック---------------------------------------------------------------------------
def Lv_up_check(pt0: dict, pt: dict, bm: BattleManager) -> dict:
    """
    経験値超過分のレベルアップを繰り返し処理する。

    pt0: 変更対象のモンスターデータ
    pt : 上昇前のスナップショット（pr_Lv_up での差分表示用）
    """
    original_lv = pt.get("lv", 1)

    # 複数レベルアップを一度に処理するためループを使う
    while pt0.get("exp", 0) >= pt0.get("n_exp", 1):
        pt0 = Lv_up(pt0)
        if pt0["lv"] >= pt0.get("mlv", 99):
            pt0 = Lv_Max(pt0)
            bm.log_custom(pr_Lv_Max(pt0, pt))
            return pt0

    if pt0["lv"] > original_lv:
        bm.log_custom(pr_Lv_up(pt0, pt))
    return pt0


# 報酬獲得処理群 -------------------------------------
def key_get(bm: BattleManager) -> None:
    """
    最深部到達時の鍵抽選処理。
    現在の挑戦フロアが鍵の最深部と一致した場合のみ発動する。
    """
    event_boost = Conf.get("event_boost")
    vip_boost = bm.vips.get("boost")

    # 鍵抽選は最深部への挑戦時のみ。前のフロアを再戦しても発動しない
    if bm.in_floor == bm.user.get("key", 1):
        # key: 獲得階層数, value: 表示テキスト。key=0 は「何も起きない」ケース
        key_sets = {
            0: 0,
            1: "普通の鍵+1",
            3: "幸せの鍵+3",
            10: "幸運の鍵+10",
            30: "天運の鍵+30",
            50: "希望の鍵+50",
            100: "奇跡の鍵+100",
        }

        # ブースト状態によって各鍵の出現重みが変わる
        if event_boost and vip_boost:
            w = [0, 40, 22, 16, 10, 7, 5]
        elif event_boost or vip_boost:
            w = [3, 50, 18, 14, 8, 4, 3]
        else:
            w = [12, 52, 15, 10, 6, 3, 2]

        get, txt = random.choices(list(key_sets.items()), weights=w)[0]
        if get != 0:
            bm.user["key"] = bm.user.get("key", 1) + get
            bm.log_custom({"type": "key_get", "item_name": txt})


# メダル獲得処理---------------------------------------------------------------------------
def battle_medal_get(bm: BattleManager) -> None:
    """わたぼう戦勝利時のメダル獲得処理。階層が深いほど獲得数が多い"""
    event_boost = Conf.get("event_boost")
    vip_boost = bm.vips.get("boost")

    # ブースト状態別の階層ごと獲得数テーブル [~500F, ~1000F, ~10000F, 10001F~]
    if event_boost and vip_boost:
        arr = [10, 14, 20, 30]
    elif event_boost or vip_boost:
        arr = [5, 7, 10, 15]
    else:
        arr = [3, 5, 7, 10]

    if bm.in_floor <= 500:
        get = arr[0]
    elif bm.in_floor <= 1000:
        get = arr[1]
    elif bm.in_floor <= 10000:
        get = arr[2]
    else:
        get = arr[3]

    bm.user["medal"] = bm.user.get("medal", 0) + get
    bm.log_custom({"type": "medal_get", "amount": get})


# 部屋鍵獲得処理---------------------------------------------------------------------------
def battle_roomkey_get(bm: BattleManager) -> None:
    """スライム戦勝利時の部屋鍵選択処理。未取得の鍵がある場合のみ選択肢を表示する"""
    options = [name for name, r_key in bm.room_key.items() if r_key.get("get", 0) == 0]
    if options:
        bm.log_custom({"type": "roomkey", "options": options})


# 異世界鍵獲得処理---------------------------------------------------------------------------
def battle_isekai_limit_get(bm: BattleManager) -> None:
    """
    VIPSガールズ戦勝利時の異世界探索リミット解放処理。
    初回は 10 に設定し、以降は +10 ずつ拡張する。
    """
    if bm.user.get("isekai_limit", 0):
        bm.user["isekai_limit"] += 10
        isekai_limit_next = True  # 既存リミットをさらに拡張した
    else:
        bm.user["isekai_limit"] = 10
        isekai_limit_next = False  # 初めてリミットが解放された

    bm.log_custom({"type": "isekai_limit", "isekai_limit_next": isekai_limit_next})


def battle_isekai_key_get(bm: BattleManager) -> None:
    """
    異世界戦闘勝利時の探索鍵更新処理。
    現在の探索フロアが鍵の最深部と一致した場合にのみ次の階層へ進める。
    """
    if bm.in_floor == bm.user.get("isekai_key", 0):
        # 探索リミットに達している場合はキーを進めない
        is_limit = bm.user.get("isekai_limit", 0) == bm.user.get("isekai_key", 0)

        if not is_limit:
            bm.user["isekai_key"] += 1
        bm.log_custom({"type": "isekai_key", "is_limit": is_limit})


# 勝利時モンスター獲得処理---------------------------------------------------------------------------
def mon_get(bm: BattleManager) -> None:
    """
    戦闘勝利後のモンスター仲間加入抽選処理。
    深い階層ほど抽選分母が大きくなり加入しにくくなる。
    異世界では特に低確率（1/50）になる。
    """
    if bm.in_floor <= 150:
        get = random.randint(1, 3)
    elif bm.in_floor <= 200:
        get = random.randint(1, 4)
    else:
        get = random.randint(1, 5)

    if bm.special == "異世界":
        get = random.randint(1, 50)

    # get == 1 のときのみ仲間加入イベントが発生する
    if get == 1:
        M_list = open_monster_dat()
        get_name = bm.battle["teki"][0].get("name")

        # マスターデータの "get" フラグが 1 のモンスターのみ仲間加入対象
        if get_name and M_list.get(get_name, {}).get("get", 1) == 1:
            bm.log_custom({"type": "monget", "name": get_name})


# 敗戦処理---------------------------------------------------------------------------
def haisen(bm: BattleManager) -> None:
    """
    敗北時の鍵ペナルティ処理。
    鍵が 10 以下の場合はペナルティなし。
    鍵が多いほど大きなペナルティが発生する可能性がある。
    """
    u_key = bm.user.get("key", 1)
    if u_key <= 10:
        return

    # 所持鍵の量によって抽選テーブルとその重みを切り替える
    if 11 <= u_key <= 100:
        key_sets = {
            1: "不幸の鍵-1",
            3: "不運な鍵-3",
            5: "呪いの鍵-5",
            10: "危険な鍵-10",
        }
        w = [50, 30, 19, 1]
    elif u_key <= 1000:
        key_sets = {
            1: "不幸の鍵-1",
            3: "不運な鍵-3",
            5: "呪いの鍵-5",
            10: "危険な鍵-10",
            50: "絶望の鍵-50",
            100: "絶対絶命の鍵-100",
        }
        w = [46, 21, 16, 11, 5, 1]
    else:  # 1001 <= u_key
        key_sets = {
            1: "不幸の鍵-1",
            3: "不運な鍵-3",
            5: "呪いの鍵-5",
            10: "危険な鍵-10",
            50: "絶望の鍵-50",
            100: "絶対絶命の鍵-100",
            0: "",  # 特大ペナルティのプレースホルダ。後続の if get == 0 で置き換えられる
        }
        w = [46, 20, 15, 10, 5, 3, 1]

    get, txt = random.choices(list(key_sets.items()), weights=w)[0]

    if get == 0:
        # 1001 階以上の特大ペナルティ: 所持鍵の 1/5 を失う
        get = int(u_key / 5)
        txt = f"終焉の鍵-{get}"

    bm.user["key"] -= get
    bm.log_custom({"type": "haisen", "item_name": txt})


# 戦闘終了メイン処理---------------------------------------------------------------------------
def battle_end(Fend: str, s: float, bm: BattleManager) -> None:
    """
    戦闘終了のメイン処理。

    s: 勝敗係数（1=勝利, 0=敗北, 0.5=引き分け）。
       s=0 の場合は経験値・お金を付与しない。
    Fend: 結果テキスト（テンプレート表示用）
    """
    base_exp = bm.battle["teki"][0].get("exp", 0)
    base_money = bm.battle["teki"][0].get("money", 0)
    # 経験値は出撃数(pt_num)で均等割り
    exp = max(int(base_exp * s / bm.pt_num), 0)
    money = int(base_money * s)

    # ブースト状態によって経験値・お金を 2〜4 倍にする
    if Conf.get("event_boost") and bm.vips.get("boost"):
        exp *= 4
        money *= 4
    elif Conf.get("event_boost") or bm.vips.get("boost"):
        exp *= 2
        money *= 2

    bm.log_custom(
        {
            "type": "battle_end",
            "result": Fend,
            "money": slim_number_with_cookie(money),
            "exp": slim_number_with_cookie(exp),
        }
    )

    # s=0（敗北）の場合は経験値・お金を付与しない
    if s != 0:
        bm.user["money"] = min(int(bm.user.get("money", 0) + money), 99999999999999)

        # 生存中かつ最大レベル未到達のモンスターにのみ経験値を付与する。
        # pt.copy() を渡してレベルアップ前のスナップショットを保持し、
        # Lv_up_check 内で上昇前後の差分を計算させる
        for i, pt in enumerate(bm.battle["party"]):
            if pt.get("hp", 0) > 0 and pt.get("lv", 1) != pt.get("mlv", 99):
                pt["exp"] = pt.get("exp", 0) + exp
                bm.battle["party"][i] = Lv_up_check(pt, pt.copy(), bm)
