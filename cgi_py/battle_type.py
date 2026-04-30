# battle_type.py - 戦闘種類分け

import time
import random
from cgi_py.battle.battle_encount import battle_encount
from cgi_py.battle.battle_menu import battle_menu
from sub_def.file_ops import open_user_all, save_user_all
from sub_def.utils import error, print_html
from sub_def.crypto import set_session

import conf

Conf = conf.Conf


def validate_user_and_party(user, party, in_floor=None, in_isekai=None):
    """ユーザーとパーティの状態をチェック"""
    if in_floor is not None:
        if not (0 < in_floor <= user.get("key", 1)):
            error("階層指定がおかしいです", jump="my_page")

    if in_isekai is not None:
        if not (0 <= in_isekai <= user.get("isekai_key", 0)):
            error("異世界は1Fづつしか進めません。", jump="my_page")
        if in_isekai > user.get("isekai_limit", 0):
            error("探索限界に達しています", jump="my_page")

    if len(party) < 1:
        error("パーティがいません。最低1体は必要です。", jump="my_page")
    if party[0].get("hp", 0) <= 0:
        error(
            "先頭のモンスターのHPが0です。<br>回復するか他のモンスターにしてください。",
            jump="my_page",
        )


def determine_special_enemy(user, vips, room_key, in_floor):
    """
    特殊敵を判定する。
    """
    vip_boost = vips.get("boost")
    event_boost = Conf.get("event_boost")

    if event_boost and vip_boost:
        randam = 15
    elif event_boost or vip_boost:
        randam = 20
    else:
        randam = 25

    special_enemies = ["わたぼう"] if random.randint(1, randam) == 1 else []

    # 特殊条件判定
    if "わたぼう" in special_enemies:
        if any(r_key.get("get", 0) == 0 for r_key in room_key.values()):
            special_enemies.append("スライム")

        # 500階おきに次のエリアに進めるようになる
        if in_floor >= 1001 + 500 * (user.get("isekai_limit", 0) / 10):
            if user.get("isekai_limit", 0) < user.get("isekai_key", 0):
                if user.get("isekai_limit", 0) != Conf.get("isekai_max_limit"):
                    special_enemies.append("vipsg")

    return special_enemies or [0]  # デフォルト値として[0]を返す


def process_battle(
    FORM, user_name, session, all_data, special, floor_key, floor_value, room_value=None
):
    """
    バトルの処理を共通化。
    """
    next_t = time.time() + Conf["nextplay"]
    user = all_data.get("user", {})

    # セッションおよびユーザーデータの更新
    session[floor_key] = floor_value
    user[floor_key] = floor_value

    if room_value is not None:
        session["last_room"] = room_value
        user["last_room"] = room_value

    session["special"] = special
    session["next_t"] = next_t
    session["turn"] = 1
    user["next_t"] = next_t

    # ユーザーデータを一括保存
    all_data["user"] = user
    save_user_all(all_data, user_name)

    # セッションを保存してFORMに上書き（以降の戦闘モジュールで参照するため）
    set_session(session)
    FORM["s"] = session

    encount_data = battle_encount(FORM, special)
    menu_data = battle_menu(FORM, special)

    print_html(
        "battle_layout_tmp.html",
        {
            "Conf": Conf,
            "token": session.get("token", ""),
            "encount_data": encount_data,
            "menu_data": menu_data,
        },
    )


def battle_type(FORM):
    """通常のバトルエントリーポイント"""
    session = FORM.get("s", {})
    user_name = session.get("in_name")

    if not user_name:
        error("ユーザー名が取得できませんでした。", jump="top")

    in_floor = int(FORM.get("in_floor", 1))
    in_room = FORM.get("in_room", "")

    # データを一括で読み込み
    all_data = open_user_all(user_name)
    user = all_data.get("user", {})
    party = all_data.get("party", [])
    vips = all_data.get("vips", {})
    room_key = all_data.get("room_key", {})

    validate_user_and_party(user, party, in_floor=in_floor)

    special_enemies = determine_special_enemy(user, vips, room_key, in_floor)
    selected_enemy = random.choice(special_enemies)

    process_battle(
        FORM,
        user_name,
        session,
        all_data,
        selected_enemy,
        "last_floor",
        in_floor,
        room_value=in_room,
    )


def battle_type2(FORM):
    """異世界のバトルエントリーポイント"""
    session = FORM.get("s", {})
    user_name = session.get("in_name")

    if not user_name:
        error("ユーザー名が取得できませんでした。", jump="top")

    in_isekai = int(FORM.get("in_isekai", 0))

    # データを一括で読み込み
    all_data = open_user_all(user_name)
    user = all_data.get("user", {})
    party = all_data.get("party", [])

    validate_user_and_party(user, party, in_isekai=in_isekai)

    process_battle(
        FORM, user_name, session, all_data, "異世界", "last_floor_isekai", in_isekai
    )
