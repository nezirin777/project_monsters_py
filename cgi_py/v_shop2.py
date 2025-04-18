# 100vips = 50メダル,10vips = 5メダル,1vips = 0.5メダル
import sub_def


def v_shop2_ok(FORM):
    m_name = FORM["m_name"]
    token = FORM["token"]

    if not (FORM.get("m_name")):
        sub_def.error("対象が選択されていません。")

    vips = sub_def.open_vips()
    user = sub_def.open_user()
    vshop_list = sub_def.open_vips_shop2_dat()

    item = vshop_list.get(m_name)
    if not item:
        sub_def.error("指定されたアイテムが存在しません。")

    price = item["price"]

    # メダル残高チェック
    if user["medal"] < price:
        sub_def.error("メダルが足りません！")

    user["medal"] -= price

    b_name = item["b_name"]
    vips[b_name] = int(vips.get(b_name, 0)) + 1

    sub_def.save_user(user)
    sub_def.save_vips(vips)

    html = f"""
		<form action="{{ Conf.cgiurl }}" method="post">
			<input type="hidden" name="mode" value="v_shop2">
			<input type="hidden" name="token" value="{token}">
			<button type="submit">交換所に戻る</button>
		</form>
	"""

    sub_def.result(f"{m_name}を購入しました。", html, token)
