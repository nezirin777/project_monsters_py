# 100vips = 50メダル,10vips = 5メダル,1vips = 0.5メダル
from sub_def.file_ops import open_vips_shop2_dat, open_user_all, save_user_all
from sub_def.utils import print_html, get_and_clear_flash, error, success
from sub_def.monster_ops import monster_select
import conf

Conf = conf.Conf


def v_shop2_ok(FORM):
    user_name = FORM["s"]["in_name"]
    m_name = FORM["m_name"]

    if not (FORM.get("m_name")):
        error("対象が選択されていません。", jump="v_shop2")

    user_all = open_user_all(user_name)
    user = user_all.get("user", {})
    vips = user_all.get("vips", {})

    vshop_list = open_vips_shop2_dat()

    item = vshop_list.get(m_name)
    if not item:
        error("指定されたアイテムが存在しません。", jump="my_page")

    price = item["price"]

    # メダル残高チェック
    if user["medal"] < price:
        error("メダルが足りません！", jump="my_page")

    user["medal"] -= price

    b_name = item["b_name"]
    vips[b_name] = int(vips.get(b_name, 0)) + 1

    user_all["user"] = user
    user_all["vips"] = vips
    save_user_all(user_all, user_name)

    success(f"【{m_name}】を購入しました！", jump="v_shop2")
