# battle_sub.py

import random
import conf
from sub_def.file_ops import open_monster_dat
from sub_def.utils import slim_number_with_cookie

Conf = conf.Conf


# LVup処理---------------------------------------------------------------------------
def Lv_up(pt0):
    GROWTH_RATES = {
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

    pt0["lv"] = pt0.get("lv", 1) + 1
    pt0["exp"] = pt0.get("exp", 0) - int(pt0.get("n_exp", 0))

    for max_lv, rate in GROWTH_RATES["exp_rates"]:
        if pt0["lv"] <= max_lv:
            x = rate
            break
    else:
        x = 1

    pt0["n_exp"] = min(
        int(pt0.get("n_exp", 0) * x), int(pt0["lv"] * 1000), GROWTH_RATES["max_exp"]
    )

    factors = {
        "mhp": [0.8, 0.9, 1.0, 1.1, 1.2],
        "mmp": [0.7, 0.8, 0.9, 1.0, 1.1],
        "atk": [0.8, 0.9, 1.0, 1.1, 1.2],
        "def": [0.7, 0.8, 0.9, 1.0, 1.1],
        "agi": [0.7, 0.8, 0.9, 1.0, 1.1],
    }
    hosei = pt0.get("hai", 0) * 0.1

    def calculate_growth(base_value, random_factors, level):
        lan = random.choice(random_factors)
        return int(lan * base_value / level)

    for stat, rand_factors in factors.items():
        base_val = pt0.get(stat, 1)
        growth = calculate_growth(base_val, rand_factors, pt0["lv"])

        # HP/ATK：ステータスが1の時無条件で+1、2のときは50％で+1、3以上は従来の判定。
        if stat in ["mhp", "atk"]:
            if base_val == 1:
                pt0[stat] += 1
            elif base_val == 2:
                pt0[stat] += random.choice([0, 1])
            else:
                pt0[stat] += int(growth + hosei)
        else:
            pt0[stat] += int(growth + hosei)

    return pt0


def Lv_Max(pt0):
    hai = pt0.get("hai", 0)
    pt0["lv"] = pt0.get("mlv", 1)
    pt0["mhp"] = hai + 15
    pt0["mmp"] = hai + 14
    pt0["atk"] = hai + 25
    pt0["def"] = hai + 24
    pt0["agi"] = hai + 24
    pt0["exp"] = 0
    pt0["n_exp"] = 0
    pt0["hp"] = min(pt0.get("hp", 0), pt0["mhp"])
    pt0["mp"] = min(pt0.get("mp", 0), pt0["mmp"])
    return pt0


# LVup出力処理---------------------------------------------------------------------------
def pr_Lv_up(pt0, pt):
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


def pr_Lv_Max(pt0, pt):
    return {
        "type": "lvup",
        "name": pt.get("name", ""),
        "old_lv": pt.get("lv", 1),
        "new_lv": pt0.get("lv", 99),
        "is_max": True,
    }


# LVupチェック---------------------------------------------------------------------------
def Lv_up_check(pt0, pt):
    logs = []
    original_lv = pt.get("lv", 1)

    while pt0.get("exp", 0) >= pt0.get("n_exp", 1):
        pt0 = Lv_up(pt0)
        if pt0["lv"] >= pt0.get("mlv", 99):
            pt0 = Lv_Max(pt0)
            logs.append(pr_Lv_Max(pt0, pt))
            return pt0, logs

    if pt0["lv"] > original_lv:
        logs.append(pr_Lv_up(pt0, pt))
    return pt0, logs


# 報酬獲得処理群 -------------------------------------
def key_get(in_floor, user, vips):
    vip_boost = vips.get("boost")
    event_boost = Conf.get("event_boost")

    if in_floor == user.get("key", 1):
        key_sets = {
            0: 0,
            1: "普通の鍵+1",
            3: "幸せの鍵+3",
            10: "幸運の鍵+10",
            30: "天運の鍵+30",
            50: "希望の鍵+50",
            100: "奇跡の鍵+100",
        }

        if event_boost and vip_boost:
            w = [0, 40, 22, 16, 10, 7, 5]
        elif event_boost or vip_boost:
            w = [3, 50, 18, 14, 8, 4, 3]
        else:
            w = [12, 52, 15, 10, 6, 3, 2]

        get, txt = random.choices(list(key_sets.items()), weights=w)[0]

    if get != 0:
        user["key"] = user.get("key", 1) + get
        return {
            "type": "message",
            "css_class": "battle_keyget",
            "text": f"<span class='yellow'>{txt}</span>を拾った！ラッキー♪",
        }

    return None


# 部屋鍵獲得処理---------------------------------------------------------------------------
def battle_roomkey_get(token, room_key_data):
    options = [
        name for name, r_key in room_key_data.items() if r_key.get("get", 0) == 0
    ]
    if not options:
        return None
    return {"type": "roomkey", "options": options}


# 異世界鍵獲得処理---------------------------------------------------------------------------
def battle_isekai_limit_get(user):
    if user.get("isekai_limit", 0):
        user["isekai_limit"] += 10
        txt = "異世界をより深く探索できるようになった!"
    else:
        user["isekai_limit"] = 10
        txt = "異世界への扉の鍵をGetした!"

    return {
        "type": "message",
        "css_class": "battle_keyget",
        "text": f"<span class='yellow'>{txt}</span>",
    }


def battle_isekai_key_get(in_isekai, user):
    txt = ""
    if in_isekai == user.get("isekai_key", 0):
        if user.get("isekai_limit", 0) == user.get("isekai_key", 0):
            txt = f"探索限界に到達した。"
        else:
            txt = f"次の階層の鍵を手に入れた。"
            user["isekai_key"] += 1

    return {
        "type": "message",
        "css_class": "battle_keyget",
        "text": f"<span class='yellow'>{txt}</span>",
    }


# メダル獲得処理---------------------------------------------------------------------------


def battle_medal_get(in_floor, user, vips):
    vip_boost = vips.get("boost")
    event_boost = Conf.get("event_boost")

    if event_boost and vip_boost:
        arr = [10, 14, 20, 30]
    elif event_boost or vip_boost:
        arr = [5, 7, 10, 15]
    else:
        arr = [3, 5, 7, 10]

    if in_floor <= 500:
        get = arr[0]
    elif 501 <= in_floor <= 1000:
        get = arr[1]
    elif 1001 <= in_floor <= 10000:
        get = arr[2]
    else:
        get = arr[3]

    user["medal"] = user.get("medal", 0) + get
    return {
        "type": "message",
        "css_class": "battle_keyget",
        "text": f"<span class='yellow'>メダルを{get}枚ゲットした！ラッキー♪</span>",
    }


# 勝利時モンスター獲得処理---------------------------------------------------------------------------
def mon_get(in_floor, special, token, battle, zukan):
    if in_floor <= 150:
        get = random.randint(1, 3)
    elif 151 <= in_floor <= 200:
        get = random.randint(1, 4)
    else:
        get = random.randint(1, 5)

    if special == "異世界":
        get = random.randint(1, 50)

    if get == 1:
        M_list = open_monster_dat()
        get_name = battle["teki"][0].get("name")

        if not get_name:
            return None

        # モンスターデータと図鑑情報を確認
        if M_list.get(get_name, {}).get("get", 1) == 1:
            return {"type": "monget", "name": get_name}

    return None


# 敗戦処理---------------------------------------------------------------------------
def haisen(user):
    if user.get("key", 1) <= 10:
        return ""

    u_key = user.get("key", 1)
    w = [100]
    key_sets = {1: "不幸の鍵-1"}

    if 11 <= u_key <= 100:
        key_sets = {
            1: "不幸の鍵-1",
            3: "不運な鍵-3",
            5: "呪いの鍵-5",
            10: "危険な鍵-10",
        }
        w = [50, 30, 19, 1]
    elif 101 <= u_key <= 1000:
        key_sets = {
            1: "不幸の鍵-1",
            3: "不運な鍵-3",
            5: "呪いの鍵-5",
            10: "危険な鍵-10",
            50: "絶望の鍵-50",
            100: "絶対絶命の鍵-100",
        }
        w = [46, 21, 16, 11, 5, 1]
    elif 1001 <= u_key:
        key_sets = {
            1: "不幸の鍵-1",
            3: "不運な鍵-3",
            5: "呪いの鍵-5",
            10: "危険な鍵-10",
            50: "絶望の鍵-50",
            100: "絶対絶命の鍵-100",
            0: "",
        }
        w = [46, 20, 15, 10, 5, 3, 1]

    get, txt = random.choices(list(key_sets.items()), weights=w)[0]

    if get == 0:
        get = int(u_key / 5)
        txt = f"終焉の鍵-{get}"

    user["key"] -= get

    return {
        "type": "message",
        "css_class": "battle_keyget",
        "text": f"<span class='red'>{txt}</span>を拾ってしまった！",
    }


# 戦闘終了メイン処理---------------------------------------------------------------------------
def battle_end(Fend, s, special, all_data, battle):
    user = all_data.get("user", {})
    party = all_data.get("party", [])
    vips = all_data.get("vips", {})

    pt_num = 1 if special in ("わたぼう", "スライム") else min(len(party), 3)

    base_exp = battle["teki"][0].get("exp", 0)
    base_money = battle["teki"][0].get("money", 0)
    exp = max(int(base_exp * s / pt_num), 0)
    money = int(base_money * s)

    vip_boost = vips.get("boost")
    event_boost = Conf.get("event_boost")

    if event_boost and vip_boost:
        exp *= 4
        money *= 4
    elif event_boost or vip_boost:
        exp *= 2
        money *= 2

    exp2 = slim_number_with_cookie(exp)
    money2 = slim_number_with_cookie(money)

    logs = [
        {
            "type": "message",
            "css_class": "battle_log_Lvup",
            "text": f"戦闘に<span class='red'>{Fend}</span><br><span class='sky_blue'>{money2}</span>Gを得た。<br>それぞれ<span class='sky_blue'>{exp2}</span>ポイントの経験値を得た。",
        }
    ]

    if s != 0:
        user["money"] = min(int(user.get("money", 0) + money), 99999999999999)
        # パーティの経験値更新とレベルアップチェック
        for i, pt in enumerate(battle["party"]):
            if pt.get("hp", 0) <= 0:
                continue
            if pt.get("lv", 1) != pt.get("mlv", 99):
                pt0 = pt.copy()
                pt0["exp"] = pt0.get("exp", 0) + exp

                pt0, lv_logs = Lv_up_check(pt0, pt)
                logs.extend(lv_logs)  # リストを追加
                battle["party"][i] = pt0.copy()

    # battleに保存された最新のステータスを、大元のpartyに反映
    for i, pt in enumerate(battle["party"]):
        party[i] = pt

    if party[0].get("hp", 0) == 0:
        party[0]["hp"] = 1

    # 変更を大元のall_dataに適用
    all_data["user"] = user
    all_data["party"] = party

    return all_data, logs
