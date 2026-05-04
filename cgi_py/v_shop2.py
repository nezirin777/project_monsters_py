# v_shop2 - アイテム(パーク)購入処理
# 100vips = 50メダル,10vips = 5メダル,1vips = 0.5メダル
from sub_def.file_ops import open_vips_shop2_dat, open_user_all, save_user_all
from sub_def.utils import error, success
import conf

Conf = conf.Conf


def v_shop2_ok(FORM):
    session = FORM.get("s", {})
    user_name = session.get("in_name")
    m_name = FORM.get("m_name")

    if not m_name:
        error("対象が選択されていません。", jump="v_shop2")

    user_all = open_user_all(user_name)
    user = user_all.get("user", {})
    vips = user_all.get("vips", {})

    vshop_list = open_vips_shop2_dat()

    # 不正なm_name対策
    item = vshop_list.get(m_name)
    if not item:
        error("指定されたアイテムが存在しません。", jump="v_shop2")

    price = int(item.get("price", 0))

    # メダル残高チェック
    if int(user.get("medal", 0)) < price:
        error("メダルが足りません！", jump="my_page")

    user["medal"] = int(user.get("medal", 0)) - price

    b_name = item.get("b_name", m_name)
    vips[b_name] = int(vips.get(b_name, 0)) + 1

    user_all["user"] = user
    user_all["vips"] = vips
    save_user_all(user_all, user_name)

    success(f"【{m_name}】を購入しました！", jump="v_shop2")
