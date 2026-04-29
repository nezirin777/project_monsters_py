# my_page.py - マイページ表示処理,ログイン後の基本画面。

import datetime

from sub_def.file_ops import (
    open_omiai_list,
    open_user_list,
    save_user_list,
    open_user_all,
    save_user_all,
)
from sub_def.utils import print_html, slim_number_with_cookie, get_and_clear_flash
from sub_def.user_ops import get_host

import conf

Conf = conf.Conf


def calculate_costs_and_options(party):
    """宿屋・教会のコスト計算および配合・転換オプションを生成"""
    yadoya_cost = 0
    kyoukai_cost = 0
    haigou_options = []
    tenkan_options = []

    for i, pt in enumerate(party, 1):
        if pt["hp"] != 0:
            yadoya_cost += (pt["mhp"] - pt["hp"]) + (pt["mmp"] - pt["mp"])
        else:
            kyoukai_cost += (pt["mhp"] + pt["mmp"]) * 2

        if pt["lv"] >= Conf["haigoulevel"]:
            haigou_options.append(
                {
                    "index": i,
                    "name": pt["name"],
                    "sex": pt["sex"],
                    "lv": pt["lv"],
                    "hai": pt["hai"],
                }
            )

        if pt["lv"] == 1:
            tenkan_options.append(
                {
                    "index": i,
                    "name": pt["name"],
                    "sex": pt["sex"],
                    "cost": pt["hai"] * 100,
                }
            )

    return yadoya_cost, kyoukai_cost, haigou_options, tenkan_options


def update_user_list(in_name, user, party):
    """ユーザー一覧（グローバル）を更新"""
    u_list = open_user_list()
    bye = datetime.datetime.now() + datetime.timedelta(days=Conf["goodbye"])
    s = 3

    # party を最大3体までに整形
    display_party = party[:s] + [{} for _ in range(s - len(party))]

    u_list[in_name] |= {
        "host": get_host(),
        "bye": bye.strftime("%Y-%m-%d"),
        "key": user.get("key", 1),
        "money": user.get("money", 0),
        "getm": user.get("getm", "0／0匹(0％)"),
        **{
            f"m{i+1}_{attr}": display_party[i].get(attr, "")
            for i in range(s)
            for attr in ["name", "lv", "hai"]
        },
    }
    save_user_list(u_list)


def my_page(FORM):
    """マイページ表示処理（user_all 完全対応版）"""

    session = FORM.get("s", {})

    # ユーザー名は FORM["s"] を優先して取得
    in_name = session.get("in_name")
    if not in_name:
        in_name = FORM.get("name")
    if not in_name:
        # 念のためエラー処理（通常はここには来ないはず）
        from sub_def.utils import error

        error("ユーザー名が取得できませんでした。", jump="top")

    token = session.get("token")

    # Flashメッセージの取得とクリア（一番最初に呼ぶ）
    flash_msg, flash_type = get_and_clear_flash(FORM["s"])

    last_floor = int(session.get("last_floor", 1))
    last_room = session.get("last_room", "")
    last_floor_isekai = int(session.get("last_floor_isekai", 0))
    next_t = float(session.get("next_t", 0))

    omiai_list = open_omiai_list()

    # === 新形式：user_all で一括取得 ===
    all_data = open_user_all(in_name)

    user = all_data.get("user", {})
    party = all_data.get("party", [])
    vips = all_data.get("vips", {})
    room_key = all_data.get("room_key", {})
    waza = all_data.get("waza", {})

    # ユーザーリスト更新
    update_user_list(in_name, user, party)

    # ブーストの有効期限チェック
    now_ts = datetime.datetime.now().timestamp()
    boost_until = vips.get("boost")

    boost_flg = False
    boost_remain_sec = 0

    if boost_until is not None and boost_until > now_ts:
        boost_flg = True
        boost_remain_sec = int(boost_until - now_ts)
    elif boost_until is not None:
        # 期限切れ → Noneにリセットして保存
        vips["boost"] = None
        all_data["vips"] = vips
        save_user_all(all_data, in_name)

    hours = boost_remain_sec // 3600
    minutes = (boost_remain_sec % 3600) // 60
    seconds = boost_remain_sec % 60
    boost_time = f"{hours}時間{minutes}分{seconds}秒"

    # 追加情報生成
    isekai, isekai_next = (
        ("hidden", "")
        if not user.get("isekai_limit")
        else ("", min(user.get("isekai_key", 0), user.get("isekai_limit", 0)))
    )
    park_get = "" if vips.get("パーク") else "hidden"

    # 表示用データ準備
    option_list = list(range(1, len(party) + 1))
    party_with_index = list(enumerate(slim_number_with_cookie(party), 1))
    user_v = slim_number_with_cookie(user)

    # 鍵の表示リスト
    room_key_display = [
        {
            "name": name,
            "has_key": r_key.get("get", 0) == 1,
            "selected": (last_room == name),
        }
        for name, r_key in room_key.items()
    ]

    # 技の表示リスト
    waza_display = [
        {"name": name if wa.get("get", 0) == 1 else "-"} for name, wa in waza.items()
    ]

    # お見合い状況
    omiai_status = (
        "baby"
        if omiai_list.get(in_name, {}).get("baby")
        else (
            "request"
            if any(in_name == omiai.get("request") for omiai in omiai_list.values())
            else ""
        )
    )

    # 宿屋・教会コスト計算
    yadoya_cost, kyoukai_cost, haigou_options, tenkan_options = (
        calculate_costs_and_options(party)
    )

    yadoya_cost_v = slim_number_with_cookie(yadoya_cost)
    kyoukai_cost_v = slim_number_with_cookie(kyoukai_cost)

    # テンプレートに渡すデータ
    content = {
        "my_page_flg": 1,
        "Conf": Conf,
        "in_name": in_name,
        "token": token,
        "next_t": next_t,
        "isekai": isekai,
        "isekai_next": isekai_next,
        "last_floor": last_floor,
        "last_floor_isekai": last_floor_isekai,
        "park_get": park_get,
        "user": user,
        "user_v": user_v,
        "boost_flg": boost_flg,
        "boost_time": boost_time,
        "party_with_index": party_with_index,
        "option_list": option_list,
        "room_key_display": room_key_display,
        "waza_display": waza_display,
        "omiai_status": omiai_status,
        "yadoya_cost": yadoya_cost,
        "kyoukai_cost": kyoukai_cost,
        "yadoya_cost_v": yadoya_cost_v,
        "kyoukai_cost_v": kyoukai_cost_v,
        "haigou_options": haigou_options,
        "tenkan_options": tenkan_options,
        "flash_msg": flash_msg,
        "flash_type": flash_type,
    }

    print_html("my_page_tmp.html", content)
