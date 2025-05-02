from jinja2 import Environment, FileSystemLoader
import sub_def
import conf

env = Environment(loader=FileSystemLoader("templates"), cache_size=100)

categories = [
    {"name": "メダル", "val1": "メダル", "val2": "枚"},
    {"name": "G", "val1": "", "val2": "ゴールド"},
]


def render_shop(user_v, item_lists, mode, token):
    """共通テンプレートをレンダリングする関数"""
    template = env.get_template("medal_shop_tmp.html")
    return template.render(user_v=user_v, item_lists=item_lists, mode=mode, token=token)


def prepare_item_lists(
    shop_data, categories, additional_filter=None, price_modifier=None
):
    """
    アイテムリストをカテゴリ別に分類する共通関数。

    shop_data: ショップのデータ
    categories: カテゴリ情報のリスト
    additional_filter: アイテムを絞り込むための追加条件（任意）
    price_modifier: 価格を修正する関数（任意）
    """
    return {
        category["name"]: [
            {
                "name": name,
                "price": sub_def.slim_number(
                    price_modifier(name, item) if price_modifier else item["price"]
                ),
                "val1": category["val1"],
                "val2": category["val2"],
            }
            for name, item in shop_data.items()
            if item["type"] == category["name"]
            and (not additional_filter or additional_filter(name, item))
        ]
        for category in categories
    }


def medal_shop(FORM):
    Medal_list = sub_def.slim_number(sub_def.open_medal_shop_dat())
    user_v = sub_def.slim_number(sub_def.open_user())

    item_lists = prepare_item_lists(Medal_list, categories)
    html = render_shop(user_v, item_lists, "medal_shop_ok", FORM["token"])
    sub_def.print_result("交換したいモンスターを選んでください", html, FORM["token"])


def v_shop(FORM):
    vips = sub_def.open_vips()
    zukan = sub_def.open_zukan()
    vshop_list = sub_def.open_vips_shop_dat()
    user_v = sub_def.slim_number(sub_def.open_user())

    def additional_filter(name, item):
        return zukan[item["b_name"]]["get"]

    def price_modifier(name, item):
        return item["price"] + item["price"] * vips.get(name, 0)

    item_lists = prepare_item_lists(
        vshop_list, categories, additional_filter, price_modifier
    )
    html = render_shop(user_v, item_lists, "v_shop_ok", FORM["token"])
    sub_def.print_result(
        "交換したいモンスターを選んでください<br>交換回数に応じて値段が上がっていきます",
        html,
        FORM["token"],
    )


def v_shop2(FORM):
    vips = sub_def.open_vips()
    vshop_list = sub_def.open_vips_shop2_dat()
    user_v = sub_def.slim_number(sub_def.open_user())

    # 条件に応じて表示するアイテムの絞り込み
    if vips.get("パーク", 0):
        vshop_list.pop("モンスターパーク", None)
    else:
        vshop_list.pop("パーク拡大+5枠", None)

    item_lists = prepare_item_lists(vshop_list, categories)
    html = render_shop(user_v, item_lists, "v_shop2_ok", FORM["token"])
    sub_def.print_result("交換したいアイテムを選んでください", html, FORM["token"])
