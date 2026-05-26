# omiai_room.py お見合い部屋表示処理

from typing import NoReturn

import conf
from sub_def.file_ops import open_user_all, open_omiai_list
from sub_def.utils import print_html, slim_number_with_cookie, get_and_clear_flash

Conf = conf.Conf


def create_omiai_item(omiai_data: dict, target: str) -> dict:
    """テンプレートのループ等で使いやすいように辞書化する"""
    return {
        "omiai": omiai_data,
        "omiai_v": slim_number_with_cookie(omiai_data),
        "target": target,
    }


def omiai_room(FORM: dict) -> NoReturn:
    session = FORM.get("s", {})
    user_name = session.get("in_name")

    # Flashメッセージの取得とクリア（一番最初に呼ぶ）
    flash_msg, flash_type = get_and_clear_flash(session)

    token = session.get("token") or FORM.get("token", "")
    page = int(FORM.get("page", 1))

    all_data = open_user_all(user_name)
    party = all_data.get("party", [])
    omiai_list = open_omiai_list()

    # ページング: 1ページ10件。p1/p2はスライス用の0始まりインデックスに変換して使う
    p2 = page * 10
    p1 = p2 - 10  # list[p1:p2] = (page-1)*10 ～ page*10-1 の10件

    # テンプレートに渡すデータ群
    my_registered = None
    baby_ready = None
    my_request_to_other = None
    requests_to_me = []
    other_monsters = []

    # request_user は if ブロック外で初期化する。
    # 自分がomiai_listに未登録でも other_monsters のフィルタ条件で参照するため。
    request_user = ""
    cancel = ""
    mes = ""

    # 自分の状態チェック
    if user_name in omiai_list:
        omiai = omiai_list[user_name]
        request_user = omiai.get("request", "")
        cancel = omiai.get("cancel", "")
        mes = omiai.get("mes", "")

        if not omiai.get("baby"):
            my_registered = create_omiai_item(omiai, user_name)
        else:
            baby_ready = create_omiai_item(omiai, user_name)

        # 自分に来ている申請
        for name, v in omiai_list.items():
            if v.get("request") == user_name:
                requests_to_me.append(create_omiai_item(v, name))

        # 自分が出している申請
        if request_user and request_user in omiai_list:
            my_request_to_other = create_omiai_item(
                omiai_list[request_user], request_user
            )

    # 登録されている他のモンスターを表示（現在ページの区画のみ）
    for name, v in list(omiai_list.items())[p1:p2]:
        if (
            name not in (user_name, request_user)
            and v.get("request") != user_name
            and not v.get("baby")
        ):
            other_monsters.append(create_omiai_item(v, name))

    # ページング処理
    tex_p = []
    if page > 1:
        tex_p.append({"page": page - 1, "label": "前の区画"})
    if p2 < len(omiai_list):
        tex_p.append({"page": page + 1, "label": "次の区画"})

    # 登録可能モンスター（haigoulevel に達しているものだけ表示）
    selectable_monsters = [
        {
            "index": i,
            "index_view": i + 1,
            "name": pt.get("name", ""),
            "sex": pt.get("sex", ""),
            "lv": pt.get("lv", 1),
            "hai": pt.get("hai", 0),
        }
        for i, pt in enumerate(party)
        if pt.get("lv", 0) >= Conf["haigoulevel"]
    ]

    content = {
        "Conf": Conf,
        "token": token,
        "page": page,
        "mes": mes,
        "cancel": cancel,
        "tex_p": tex_p,
        "selectable_monsters": selectable_monsters,
        "my_registered": my_registered,
        "baby_ready": baby_ready,
        "requests_to_me": requests_to_me,
        "my_request_to_other": my_request_to_other,
        "other_monsters": other_monsters,
        "flash_msg": flash_msg,
        "flash_type": flash_type,
    }

    print_html("omiai_room_tmp.html", content)
