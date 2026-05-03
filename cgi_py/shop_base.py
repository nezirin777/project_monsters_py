# shop_base.py - ショップ関連の共通関数と、メダルショップ・VIPショップの表示処理を定義

from sub_def.file_ops import (
    open_medal_shop_dat,
    open_vips_shop_dat,
    open_vips_shop2_dat,
    open_user_all,
)
from sub_def.utils import (
    get_and_clear_flash,
    slim_number_with_cookie,
    print_html,
    error,
)

import conf

Conf = conf.Conf

categories = [
    {"name": "メダル", "val1": "メダル", "val2": "枚"},
    {"name": "G", "val1": "", "val2": "ゴールド"},
]


def prepare_item_lists(
    shop_data, categories, additional_filter=None, price_modifier=None
):
    """
    アイテムリストをカテゴリ別に分類する共通関数。
    """
    return {
        category["name"]: [
            {
                "name": name,
                "price": slim_number_with_cookie(
                    price_modifier(name, item)
                    if price_modifier
                    else item.get("price", 0)
                ),
                "val1": category["val1"],
                "val2": category["val2"],
            }
            for name, item in shop_data.items()
            if item.get("type") == category["name"]
            and (not additional_filter or additional_filter(name, item))
        ]
        for category in categories
    }


def medal_shop(FORM):
    session = FORM.get("s", {})
    user_name = session.get("in_name")

    if not user_name:
        error("セッションが切れました。", jump="top")

    flash_msg, flash_type = get_and_clear_flash(session)

    Medal_list = slim_number_with_cookie(open_medal_shop_dat())
    user_all = open_user_all(user_name)

    user_v = slim_number_with_cookie(user_all.get("user", {}))
    item_lists = prepare_item_lists(Medal_list, categories)

    content = {
        "Conf": Conf,
        "token": session.get("token"),
        "mes": "交換したいモンスターを選んでください",
        "user_v": user_v,
        "item_lists": item_lists,
        "mode": "medal_shop_ok",
        "flash_msg": flash_msg,
        "flash_type": flash_type,
    }

    print_html("medal_shop_tmp.html", content)


def v_shop(FORM):
    session = FORM.get("s", {})
    user_name = session.get("in_name")

    if not user_name:
        error("セッションが切れました。", jump="top")

    flash_msg, flash_type = get_and_clear_flash(session)

    vshop_list = open_vips_shop_dat()
    user_all = open_user_all(user_name)

    user_v = slim_number_with_cookie(user_all.get("user", {}))
    vips = user_all.get("vips", {})
    zukan = user_all.get("zukan", {})

    def additional_filter(name, item):
        return zukan.get(item.get("b_name", ""), {}).get("get", 0) == 1

    def price_modifier(name, item):
        price = int(item.get("price", 0))
        return price + price * int(vips.get(name, 0))

    item_lists = prepare_item_lists(
        vshop_list, categories, additional_filter, price_modifier
    )

    content = {
        "Conf": Conf,
        "token": session.get("token"),
        "mes": "交換したいモンスターを選んでください<br>交換回数に応じて値段が上がっていきます",
        "user_v": user_v,
        "item_lists": item_lists,
        "mode": "v_shop_ok",
        "flash_msg": flash_msg,
        "flash_type": flash_type,
    }

    print_html("medal_shop_tmp.html", content)


def v_shop2(FORM):
    session = FORM.get("s", {})
    user_name = session.get("in_name")

    if not user_name:
        error("セッションが切れました。", jump="top")

    flash_msg, flash_type = get_and_clear_flash(session)

    vshop_list = open_vips_shop2_dat()
    user_all = open_user_all(user_name)

    user_v = slim_number_with_cookie(user_all.get("user", {}))
    vips = user_all.get("vips", {})

    vshop_list = dict(vshop_list)
    if vips.get("パーク", 0):
        vshop_list.pop("モンスターパーク", None)
    else:
        vshop_list.pop("パーク拡大+5枠", None)

    item_lists = prepare_item_lists(vshop_list, categories)

    content = {
        "Conf": Conf,
        "token": session.get("token"),
        "mes": "交換したいアイテムを選んでください",
        "user_v": user_v,
        "item_lists": item_lists,
        "mode": "v_shop2_ok",
        "flash_msg": flash_msg,
        "flash_type": flash_type,
    }

    print_html("medal_shop_tmp.html", content)
