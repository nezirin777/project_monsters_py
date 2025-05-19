from jinja2 import Environment, FileSystemLoader
import sub_def
import conf
import cgi_py

Conf = conf.Conf
env = Environment(
    loader=FileSystemLoader("templates"), cache_size=100
)  # テンプレートディレクトリ


def omiai_request(FORM):

    in_name = FORM["name"]
    target = FORM["target"]
    token = FORM["token"]

    # お見合いリストからデータを取得
    omiai_list = sub_def.open_omiai_list()
    my_data = omiai_list.get(in_name)
    target_data = omiai_list.get(target)

    # 自モンスターを登録済みかチェック
    if not (my_data):
        sub_def.error("あなたはまだ未登録です。<br>登録してから申請してください")

    # すでに申請がないかチェック
    if my_data["request"]:
        sub_def.error(
            "申請できるのは1人までです。<br>他の人に申請したい場合は申請をキャンセルしてからどうぞ。"
        )

    # 申請相手から依頼が来てないかチェック
    if target_data and target_data.get("request") == in_name:
        sub_def.error(f"{target}さんからはすでに依頼が来てます。")

    # 性別チェック
    if my_data["sex"] == target_data["sex"]:
        sub_def.error("性別が同じ為お見合いができません。")

    # モンスターの名前を取得し、図鑑情報をチェック
    nameA = my_data["name"]
    nameB = target_data["name"]
    my_new_mons = cgi_py.haigou_check.haigou_sub(nameA, nameB, 1)

    # 図鑑未登録の場合は「？？？」を表示
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
        mode="omiai_req",
    )

    sub_def.header()
    print(html)
    sub_def.footer()


def omiai_request_ok(FORM):

    in_name = FORM["name"]
    target = FORM["target"]
    token = FORM["token"]

    omiai_list = sub_def.open_omiai_list()

    # 自分に申請記録
    omiai_list[in_name]["request"] = target
    request_monster = omiai_list[target]["name"]

    sub_def.save_omiai_list(omiai_list)

    html = f"""
		<form action="{{ Conf.cgi_url }}" method="post">
			<input type="hidden" name="mode" value="omiai_room">
			<input type="hidden" name="token" value="{token}">
			<button type="submit">お見合い所に戻る</button>
		</form>
	"""

    sub_def.print_result(
        f"<span>{target}さん</span>の<span>{request_monster}</span>にお見合いを申請しました。",
        html,
        token,
    )


def omiai_request_cancel(FORM):

    in_name = FORM["name"]
    target = FORM["target"]
    token = FORM["token"]

    omiai_list = sub_def.open_omiai_list()

    omiai_list[in_name]["request"] = ""
    sub_def.save_omiai_list(omiai_list)

    html = f"""
		<form action="{{ Conf.cgi_url }}" method="post">
			<input type="hidden" name="mode" value="omiai_room">
			<input type="hidden" name="token" value="{token}">
			<button type="submit">お見合い所に戻る</button>
		</form>
	"""

    sub_def.print_result(f"{target}さんへの申請を取り消しました。", html, FORM["token"])
