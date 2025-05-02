from jinja2 import Environment, FileSystemLoader
import os
import sub_def
import conf

Conf = conf.Conf

# ユーザー名の使用不可文字リスト
INVALID_CHARACTERS = [
    "　",
    " ",
    "\\",
    "/",
    ";",
    ":",
    ",",
    "*",
    "?",
    "'",
    "<",
    ">",
    "|",
    '"',
    "~",
    "$",
    "&",
    "`",
    "^",
]

env = Environment(loader=FileSystemLoader("templates"), cache_size=100)
template = env.get_template("name_change_tmp.html")


# 使用不可文字チェック関数
def contains_invalid_characters(name):
    return any(char in name for char in INVALID_CHARACTERS)


# 関数：名前変更ページを表示
def name_change(FORM):
    in_name = FORM.get("name")
    token = FORM["token"]

    if sub_def.open_omiai_list().get(in_name):
        sub_def.error("お見合い所を使用中はユーザー名の変更ができません。")

    html = template.render(current_name=in_name, token=token, mode="name_change")
    sub_def.header()
    print(html)
    sub_def.my_page_button(token)


# 関数：名前変更チェックページ
def name_change_check(FORM):
    in_name = FORM["name"]
    new_name = FORM["new_name"]
    in_pass = FORM["password"]
    token = FORM["token"]

    if not new_name:
        sub_def.error("新しい名前がありません")

    if new_name == in_pass:
        sub_def.error("新しい名前とパスワードは違うものにして下さい")

    if len(new_name) > 20:
        sub_def.error("新しい名前は20文字以下で入力して下さい。")

    if contains_invalid_characters(new_name):
        sub_def.error(f"使用できない文字が含まれています。")

    if os.path.exists(Conf["savedir"] + "/" + new_name):
        sub_def.error("その名前は既に登録されています", "top")

    u_list = sub_def.open_user_list()
    if any(u_name.casefold() == new_name.casefold() for u_name in u_list):
        sub_def.error("その名前では登録することができません。", "top")

    html = template.render(
        in_name=in_name, new_name=new_name, token=token, mode="name_check"
    )
    sub_def.header()
    print(html)
    sub_def.my_page_button(token)


# 関数：名前変更の最終処理
def name_change_ok(FORM):
    in_name = FORM["name"]
    new_name = FORM["new_name"]

    u_list = sub_def.open_user_list()

    u_list[new_name] = u_list.pop(in_name)
    sub_def.save_user_list(u_list)

    user = sub_def.open_user(in_name)
    user["name"] = new_name
    sub_def.save_user(user, in_name)

    FORM["c"]["in_name"] = new_name
    sub_def.set_cookie(FORM["c"])
    sub_def.set_session(
        {"name": new_name, "password": FORM["password"], "token": FORM["token"]}
    )

    try:
        os.rename(f"{Conf["savedir"]}/{in_name}/", f"{Conf["savedir"]}/{new_name}/")
    except OSError as e:
        sub_def.error(f"名前変更中にエラーが発生しました: {e}")

    sub_def.print_result(
        f"""ユーザー名を<span>{in_name}</span>から<br><span>{new_name}</span>へと変更しました。""",
        "",
        FORM["token"],
    )
