#!D:\Python\Python314\python.exe
import sys, cgi, datetime, urllib.parse, html, json
import conf

# フォームを辞書化
form = cgi.FieldStorage()
FORM = {key: form.getvalue(key) for key in form.keys()}

# パラメーターによるセーブデータフォルダ分岐処理
conf.apply_fol(FORM)
Conf = conf.Conf

from sub_def.utils import error, print_html
from sub_def.file_ops import ensure_logfile, read_log, append_log
from sub_def.crypto import verify_csrf_token, generate_csrf_token, get_session


sys.stdout.reconfigure(encoding="utf-8")


MESSAGE_COLORS = Conf["message_colors"]


def handle_refresh(form, session):
    submitted_token = form.get("csrf_token")
    if not verify_csrf_token(submitted_token, session):
        error("不正なリクエストです", exit_code=1 if form.get("ajax") == "true" else 0)
    print("Content-Type: application/json\r\n\r\n")
    print(json.dumps({"log": read_log(), "csrf_token": session["csrf_token"]}))
    sys.exit()


def handle_post(form, session):
    submitted_token = form.get("csrf_token")
    exit_code = 1 if form.get("ajax") == "true" else 0

    if not verify_csrf_token(submitted_token, session):
        error("不正なリクエストです", exit_code)

    if "bbs_txt" not in form or not form["bbs_txt"]:
        error("発言を入力してください", exit_code)

    raw_txt = urllib.parse.unquote(form["bbs_txt"])
    if len(raw_txt) > 60:
        error("60文字以下でお願いします", exit_code)

    txt = html.escape(raw_txt[:60])  # シンプルにサニタイズ
    color = urllib.parse.unquote(form.get("color", "#000000"))
    if not isinstance(color, str) or color not in MESSAGE_COLORS:
        color = "#000000"
    if not session.get("in_name"):
        error(
            "ユーザー名が設定されていません",
            exit_code,
        )

    time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    newlog = f"""<hr><font color="{color}"><b>{session["in_name"]}</b> > {txt} <font size="1">--{time}</font></font>\n"""
    append_log(newlog)

    csrf_token = generate_csrf_token(session)

    if form.get("ajax") == "true":
        response = {"log": read_log(), "csrf_token": csrf_token}
        print("Content-Type: application/json\r\n\r\n")
        print(json.dumps(response))
        sys.stdout.flush()
        sys.exit()
    return csrf_token


def render_page(form, csrf_token):
    selected_color = form.get("color", "#000000")
    content = {
        "log": read_log(),
        "colors": MESSAGE_COLORS,
        "selected_color": selected_color,
        "csrf_token": csrf_token,
        "Conf": Conf,
    }

    print_html("bbs_tmp.html", content)


def render_view_mode():
    content = {
        "log": read_log(),
        "Conf": Conf,
    }
    print_html("bbs_view_tmp.html", content)


if __name__ == "__main__":
    # メイン処理
    session = get_session()
    csrf_token = session.get("csrf_token") or generate_csrf_token(session)

    ensure_logfile()

    if FORM.get("mode") == "refresh":
        handle_refresh(FORM, session)
    elif FORM.get("mode") == "view":  # ログ表示専用モード
        render_view_mode()
    elif "bbs_txt" in FORM:
        csrf_token = handle_post(FORM, session)
        render_page(FORM, csrf_token)
    else:
        render_page(FORM, csrf_token)
