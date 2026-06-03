# shop_base.py - ショップ関連の共通関数と、メダルショップ・VIPショップの表示処理を定義

from collections.abc import Callable
from typing import NoReturn

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

# 表示カテゴリの定義（メダル払い / G払い）
categories: list[dict] = [
    {"name": "メダル", "val1": "メダル", "val2": "枚"},
    {"name": "G", "val1": "", "val2": "ゴールド"},
]


def prepare_item_lists(
    shop_data: dict,
    categories: list[dict],
    additional_filter: Callable | None = None,
    price_modifier: Callable | None = None,
) -> dict:
    """
    アイテムリストをカテゴリ別に分類する共通関数。

    additional_filter: (name, item) -> bool  表示対象かどうかを判定する追加フィルタ
    price_modifier:    (name, item) -> int   価格を動的に計算する関数（購入回数加算等）
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


def medal_shop(FORM: dict) -> NoReturn:
    """メダル交換所の表示処理"""
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


def v_shop(FORM: dict) -> NoReturn:
    """VIP交換所1の表示処理。図鑑登録済みモンスターのみ表示し、購入回数で価格が上昇する"""
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

    def additional_filter(name: str, item: dict) -> bool:
        """図鑑に登録済みのモンスターのみ表示する"""
        return zukan.get(item.get("b_name", ""), {}).get("get", 0) == 1

    def price_modifier(name: str, item: dict) -> int:
        """購入回数に応じて価格を加算する（base + base × 購入回数）"""
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


def v_shop2(FORM: dict) -> NoReturn:
    """VIP交換所2の表示処理。パーク所持状況に応じて表示アイテムを切り替える"""
    session = FORM.get("s", {})
    user_name = session.get("in_name")

    if not user_name:
        error("セッションが切れました。", jump="top")

    flash_msg, flash_type = get_and_clear_flash(session)

    vshop_list = open_vips_shop2_dat()
    user_all = open_user_all(user_name)

    user_v = slim_number_with_cookie(user_all.get("user", {}))
    vips = user_all.get("vips", {})

    # パーク所持状況に応じて表示アイテムを切り替える
    # パーク所持済み → 「モンスターパーク」を非表示、未所持 → 「パーク拡大」を非表示
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
