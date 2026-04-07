# my_page.py

import datetime

import sub_def
import conf

Conf = conf.Conf


def calculate_costs_and_options(party):
    """宿屋・教会のコスト計算および配合・転換オプションを生成"""
    yadoya_cost, kyoukai_cost = 0, 0
    haigou_options, tenkan_options = [], []

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

    return (
        yadoya_cost,
        kyoukai_cost,
        haigou_options,
        tenkan_options,
    )


# 関数：ユーザーリストを更新
def update_user_list(in_name, user, party):
    u_list = sub_def.open_user_list()
    bye = datetime.datetime.now() + datetime.timedelta(days=Conf["goodbye"])
    s = 3

    party = party[:s] + [{} for _ in range(s - len(party))]
    u_list[in_name] |= {
        "host": sub_def.get_host(),
        "bye": bye.strftime("%Y-%m-%d"),
        "key": user["key"],
        "money": user["money"],
        "getm": user["getm"],
        **{
            f"m{i+1}_{attr}": party[i].get(attr, "")
            for i in range(s)
            for attr in [
                "name",
                "lv",
                "hai",
            ]
        },
    }
    sub_def.save_user_list(u_list)


def my_page(FORM):

    # ログイン→マイページからの処理ではpikkel読み込み時に更新されたセッションを読み込めない。
    # よってin_name付与などが必須。
    import time
    import sys

    start = time.time()

    session = FORM.get("s", {})

    in_name = session.get("in_name") or FORM.get("name")
    token = session.get("token")

    flash_msg = session.pop("flash_msg", "")
    flash_type = session.pop("flash_type", "error")

    last_floor = int(session.get("last_floor", 1))
    last_room = session.get("last_room", "")
    last_floor_isekai = int(session.get("last_floor_isekai", 0))
    next_t = float(session.get("next_t", 0))

    omiai_list = sub_def.open_omiai_list()
    user = sub_def.open_user(in_name)
    party = sub_def.open_party(in_name)
    vips = sub_def.open_vips(in_name)
    room_key = sub_def.open_room_key(in_name)
    waza = sub_def.open_waza(in_name)

    # ユーザーリスト更新
    update_user_list(in_name, user, party)

    # ブーストの有効期限チェック
    now_ts = datetime.datetime.now().timestamp()
    boost_until = vips.get("boost")

    if boost_until is not None and boost_until > now_ts:
        boost_flg = True
        boost_remain_sec = int(boost_until - now_ts)
    else:
        boost_flg = False
        boost_remain_sec = 0

        if boost_until is not None:
            vips["boost"] = None
            sub_def.save_vips(vips, in_name)

    hours = boost_remain_sec // 3600
    minutes = (boost_remain_sec % 3600) // 60
    seconds = boost_remain_sec % 60
    boost_time = f"{hours}時間{minutes}分{seconds}秒"

    # 追加情報を生成
    isekai, isekai_next = (
        ("hidden", "")
        if not user.get("isekai_limit")
        else ("", min(user["isekai_key"], user["isekai_limit"]))
    )
    park_get = "" if vips.get("パーク") else "hidden"

    # 表示用のパラメータを作成
    # インデックスを付けたリストを生成
    option_list = list(range(1, len(party) + 1))
    party_with_index = list(enumerate(sub_def.slim_number_with_cookie(party), 1))
    user_v = sub_def.slim_number_with_cookie(user)

    # 必要なデータの準備
    # 鍵のテキストリスト
    room_key_display = [
        {
            "name": name,
            "has_key": r_key["get"],
            "selected": (last_room == name),
        }
        for name, r_key in room_key.items()
    ]

    # 技のリスト
    waza_display = [{"name": name if wa["get"] else "-"} for name, wa in waza.items()]

    # お見合い状況のチェック
    omiai_status = (
        "baby"
        if omiai_list.get(in_name, {}).get("baby")
        else (
            "request"
            if any(in_name == omiai.get("request") for omiai in omiai_list.values())
            else ""
        )
    )

    yadoya_cost, kyoukai_cost, haigou_options, tenkan_options = (
        calculate_costs_and_options(party)
    )

    yadoya_cost_v = sub_def.slim_number_with_cookie(yadoya_cost)
    kyoukai_cost_v = sub_def.slim_number_with_cookie(kyoukai_cost)

    # 必要な変数を辞書にまとめてテンプレートへ渡す
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

    end = time.time()
    print(f"<!-- my_page total: {end - start:.3f} sec -->", file=sys.stderr)
    sub_def.print_html("my_page_tmp.html", content)
