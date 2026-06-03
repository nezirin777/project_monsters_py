# v_shop2.py - VIPショップ2 アイテム（パーク枠等）購入処理

# このショップはメダルのみで購入できる。価格は固定（v_shop と異なり購入回数で上昇しない）

from sub_def.file_ops import open_vips_shop2_dat, open_user_all, save_user_all
from sub_def.utils import error, success
import conf

Conf = conf.Conf


def v_shop2_ok(FORM: dict) -> None:
    """VIPショップ2でのアイテム購入処理（メダル固定、価格は購入回数によらず一定）"""
    session = FORM.get("s", {})
    user_name = session.get("in_name")
    m_name = FORM.get("m_name")

    if not m_name:
        error("対象が選択されていません。", jump="v_shop2")

    user_all = open_user_all(user_name)
    user = user_all.get("user", {})
    vips = user_all.get("vips", {})

    vshop_list = open_vips_shop2_dat()

    # 不正な m_name（画面改ざん等）への対策
    item = vshop_list.get(m_name)
    if not item:
        error("指定されたアイテムが存在しません。", jump="v_shop2")

    price = int(item.get("price", 0))

    # メダル残高チェック（このショップはメダル固定）
    if int(user.get("medal", 0)) < price:
        error("メダルが足りません！", jump="my_page")

    user["medal"] = int(user.get("medal", 0)) - price

    # b_name が設定されている場合は内部管理キーとして使用する。
    # 購入キー名（m_name）と vips の管理キーが異なる商品への対応
    b_name = item.get("b_name", m_name)
    vips[b_name] = int(vips.get(b_name, 0)) + 1

    user_all["user"] = user
    user_all["vips"] = vips
    save_user_all(user_all, user_name)

    success(f"【{m_name}】を購入しました！", jump="v_shop2")
