import time
import random
import cgi_py
import sub_def
import conf

Conf = conf.Conf


def validate_user_and_party(in_floor=None, in_isekai=None):
    """ユーザーとパーティの状態をチェック"""
    user = sub_def.open_user()
    party = sub_def.open_party()

    if in_floor is not None:
        if not (0 < in_floor <= user["key"]):
            sub_def.error("階層指定がおかしいです")

    if in_isekai is not None:
        if not (0 <= in_isekai <= user["isekai_key"]):
            sub_def.error("異世界は1Fづつしか進めません。")
        if in_isekai > user["isekai_limit"]:
            sub_def.error("探索限界に達しています")

    if len(party) < 1:
        sub_def.error("パーティがいません。最低1体は必要です。")
    if party[0]["hp"] <= 0:
        sub_def.error(
            "先頭のモンスターのHPが0です。<br>回復するか他のモンスターにしてください。"
        )
    return user, party


def determine_special_enemy(user, in_floor):
    """
    特殊敵を判定する。

    Parameters:
    - user (dict): ユーザー情報。
    - in_floor (int): 現在の階層。

    Returns:
    - list: 出現する特殊敵のリスト。
    """
    event_boost = Conf["event_boost"]
    randam = 20 if event_boost else 25
    special_enemies = ["わたぼう"] if random.randint(1, randam) == 1 else []

    # 特殊条件判定
    if "わたぼう" in special_enemies:
        room_key = sub_def.open_room_key()
        if any(r_key["get"] == 0 for r_key in room_key.values()):
            special_enemies.append("スライム")
        if in_floor >= 1001 + 500 * (user.get("isekai_limit", 0) / 10):
            # ↑500階おきに次のエリアに進めるようになる
            if user.get("isekai_limit", 0) < user.get("isekai_key", 0):
                if user.get("isekai_limit", 0) != Conf["isekai_max_limit"]:
                    special_enemies.append("vipsg")

    return special_enemies or [0]  # デフォルト値として0を返す


def process_battle(FORM, special, floor_key, floor_value):
    """
    バトルの処理を共通化。

    Parameters:
    - FORM (dict): フォームデータ。
    - special (str): 特殊敵の名前。
    - floor_key (str): クッキーに保存するフロアのキー。
    - floor_value (int): フロアの値。
    """
    next_t = time.time() + Conf["nextplay"]

    FORM["c"] |= {
        floor_key: floor_value,
        "special": special,
        "next_t": next_t,
        "turn": 1,
    }
    sub_def.set_cookie(FORM["c"])

    txt = cgi_py.battle_encount.battle_encount(FORM, special)
    txt += cgi_py.battle_menu.battle_menu(FORM, special)

    sub_def.print_html(
        "base_tmp.html",
        {
            "battle_txt": txt,
            "Conf": Conf,
        },
    )


def battle_type(FORM):
    in_floor = int(FORM["in_floor"])
    in_room = FORM["in_room"]

    user, _ = validate_user_and_party(in_floor=in_floor)
    special_enemies = determine_special_enemy(user, in_floor)
    selected_enemy = random.choice(special_enemies)

    FORM["c"] |= {
        "last_room": in_room,
    }

    process_battle(FORM, selected_enemy, "last_floor", in_floor)


def battle_type2(FORM):
    in_isekai = int(FORM["in_isekai"])

    validate_user_and_party(in_isekai=in_isekai)
    process_battle(FORM, "異世界", "last_floor_isekai", in_isekai)
