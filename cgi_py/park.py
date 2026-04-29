# park.py - モンスターパークの表示と、パーティとパークの入れ替え

from sub_def.file_ops import open_monster_dat, open_user_all, save_user_all
from sub_def.utils import (
    get_and_clear_flash,
    error,
    success,
    print_html,
    slim_number_with_cookie,
)

import conf

Conf = conf.Conf


# ソート処理関数（user_all対応版）
def sort_park(all_data, sort_v, user_name):
    """パークのソート処理を行い、user_allに反映する"""
    park = all_data["park"]

    if sort_v == 1:  # 名前順ソート
        park.sort(key=lambda x: x["name"])
    elif sort_v == 2:  # 図鑑順ソート
        mlist = open_monster_dat()
        tmp = []
        for name in mlist.keys():
            for p in park[:]:  # コピーして安全にループ
                if name == p["name"]:
                    tmp.append(p)
        park = tmp

    # 番号振り直し
    for i, ppt in enumerate(park, 1):
        ppt["no"] = i

    # user_allに反映
    all_data["park"] = park
    save_user_all(all_data, user_name)

    return park


# モンスターパーク表示関数
def park(FORM):

    user_name = FORM["s"]["in_name"]
    page = int(FORM.get("page", 1))
    sort_v = int(FORM.get("sort_v", 0))
    token = FORM["s"]["token"]

    # Flashメッセージの取得とクリア（一番最初に呼ぶ）
    flash_msg, flash_type = get_and_clear_flash(FORM["s"])

    # user_all で一括取得
    all_data = open_user_all(user_name)
    party = all_data["party"]
    park = all_data["park"]
    vips = all_data["vips"]

    if not vips.get("パーク", 0):
        error("モンスターパークを所有していません。")

    # パーク容量と預かり状況
    waku = int(vips["パーク"] * 5)
    azukari = len(park)

    # ソート処理
    if sort_v in (1, 2):
        park = sort_park(all_data, sort_v, user_name)
    else:
        # 番号振り直しだけ行う（念のため）
        for i, ppt in enumerate(park, 1):
            ppt["no"] = i

    park_v = slim_number_with_cookie(park)

    p1 = (page - 1) * 10
    p2 = min(page * 10, waku)
    jump_count = -(-len(park) // 10)

    content = {
        "Conf": Conf,
        "token": token,
        "azukari": azukari,
        "waku": waku,
        "party": party,
        "park_v": park_v,
        "jump_count": jump_count,
        "p1": p1,
        "p2": p2,
        "flash_msg": flash_msg,
        "flash_type": flash_type,
    }

    print_html("park_tmp.html", content)


# ====================#
# 手持ちを預ける
# ====================#
def park_1(FORM):
    user_name = FORM["s"]["in_name"]

    # 配列位置を合わせるため-1
    Mno = int(FORM["Mno"]) - 1

    all_data = open_user_all(user_name)
    party = all_data["party"]
    park = all_data["park"]
    vips = all_data["vips"]

    waku = vips["パーク"] * 5

    if len(park) >= waku:
        error("パークがいっぱいで預けることができませんでした。", jump="park")

    if len(party) == 1:
        error(
            "パーティーがいなくなってしまいます。<br>預けることができません。",
            jump="park",
        )

    # 先に文字列作っておかないと、預ける処理でpartyから消えてしまうため
    mes = f"""【{party[Mno]["name"]}】を預けました。"""

    # 預ける処理
    park.append(party.pop(Mno))

    # 番号振り直し
    for i, pt in enumerate(party, 1):
        pt["no"] = i
    for i, ppt in enumerate(park, 1):
        ppt["no"] = i

    # 保存（user_allにまとめて1回）
    all_data["party"] = party
    all_data["park"] = park
    save_user_all(all_data, user_name)

    success(mes, jump="park")


# ====================#
# パークから連れていく
# ====================#
def park_2(FORM):

    user_name = FORM["s"]["in_name"]
    # 配列位置を合わせるため-1
    Mno = int(FORM["mob"]) - 1

    all_data = open_user_all(user_name)
    party = all_data["party"]
    park = all_data["park"]

    # パーティーが満杯かどうか確認
    if len(party) >= 10:
        error("パーティがいっぱいで連れていくことができませんでした。", jump="park")
        return

    # 先に文字列作っておかないと、連れていく処理でparkから消えてしまうため
    mes = f"""【{park[Mno]["name"]}】をパーティに加えました。"""

    # 連れていく処理
    party.append(park.pop(Mno))

    # 番号振り直し
    for i, pt in enumerate(party, 1):
        pt["no"] = i
    for i, ppt in enumerate(park, 1):
        ppt["no"] = i

    # 保存
    all_data["party"] = party
    all_data["park"] = park
    save_user_all(all_data, user_name)

    success(mes, jump="park")
