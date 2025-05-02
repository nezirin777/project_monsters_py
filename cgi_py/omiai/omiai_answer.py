from jinja2 import Environment, FileSystemLoader
import sub_def
import conf
import cgi_py

Conf = conf.Conf
env = Environment(
    loader=FileSystemLoader("templates"), cache_size=100
)  # テンプレートディレクトリ


def omiai_answer_no(FORM):

    in_name = FORM["name"]
    target = FORM["target"]
    token = FORM["token"]

    omiai_list = sub_def.open_omiai_list()

    omiai_list[target]["request"] = ""
    omiai_list[target][
        "cancel"
    ] = f"{in_name}さんへの依頼はお断りされてしまったようです・・・"

    sub_def.save_omiai_list(omiai_list)

    html = f"""
		<form action="{{ Conf.cgiurl }}" method="post">
			<input type="hidden" name="mode" value="omiai_room">
			<input type="hidden" name="token" value="{token}">
			<button type="submit">お見合い所に戻る</button>
		</form>
	"""
    sub_def.print_result(
        f"{target}さんからの申し込みをお断りしました。", html, FORM["token"]
    )


def omiai_answer_ok(FORM):

    in_name = FORM["name"]
    target = FORM["target"]
    token = FORM["token"]

    omiai_list = sub_def.open_omiai_list()

    if omiai_list[in_name]["request"]:
        sub_def.error(
            "あなたは他の人に申請中です。<br>この人とお見合いするには申請を取り下げる必要があります。"
        )

    nameA = omiai_list[in_name]["name"]
    nameB = omiai_list[target]["name"]

    my_new_mons = cgi_py.haigou_check.haigou_sub(nameA, nameB, 1)

    zukan = sub_def.open_zukan()
    if not (zukan[my_new_mons]["get"]):
        my_new_mons = "？？？"

    # テンプレートの取得とレンダリング
    template = env.get_template("haigou_check_tmp.html")
    html = template.render(
        Conf=Conf,
        nameA=nameA,
        nameB=nameB,
        my_new_mons=my_new_mons,
        target=target,
        token=token,
        mode="omiai_ans",
    )

    sub_def.header()
    print(html)
    sub_def.footer()


def omiai_get_monster(data, new_mons, user_name):
    """新しいモンスターを生成するヘルパー関数"""
    mlv = data["lv"] + 10
    new_hai = data["hai"] + 1
    hosei = max(int(new_hai / 2), 1)
    new_mob = sub_def.monster_select(new_mons, hosei, 1, user_name)
    new_mob.update({"lv": 1, "mlv": mlv, "hai": new_hai})
    return new_mob


def omiai_answer_result(FORM):
    in_name = FORM["name"]
    target = FORM["target"]
    token = FORM["token"]

    omiai_list = sub_def.open_omiai_list()

    # 自分、相手への依頼を全キャンセル
    # 既存のリクエストをキャンセル
    for name, omiai in omiai_list.items():
        if omiai["request"] in (in_name, target):
            omiai_list[name]["request"] = ""
            omiai_list[name][
                "cancel"
            ] = f"{omiai['request']}さんへの依頼はお断りされてしまったようです・・・"

    # モンスター生成
    my_data = omiai_list[in_name]
    target_data = omiai_list[target]

    my_new_mons_name = cgi_py.haigou_check.haigou_sub(
        my_data["name"], target_data["name"], 1
    )
    target_new_mons_name = cgi_py.haigou_check.haigou_sub(
        target_data["name"], my_data["name"], 1
    )

    my_new_mons = omiai_get_monster(my_data, my_new_mons_name, in_name)
    target_new_mons = omiai_get_monster(target_data, target_new_mons_name, target)

    # データ更新
    for user_data, new_mons, partner_name in [
        (my_data, my_new_mons, target),
        (target_data, target_new_mons, in_name),
    ]:
        user_data.update(new_mons)
        user_data.update(
            {"mes": f"{partner_name}さんとのお見合いが成功しました。", "baby": 1}
        )

    sub_def.save_omiai_list(omiai_list)
    my_data = sub_def.slim_number(my_data)

    # Jinja2の環境設定とテンプレートファイルの読み込み
    template = env.get_template("new_monster_tmp.html")
    html = template.render(
        Conf=Conf,
        my_data=my_data,
        token=token,
        mode=omiai,
    )

    sub_def.header()
    print(html)
    sub_def.my_page_button(token)
