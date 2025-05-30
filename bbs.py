#!D:\Python\Python312\python.exe
import sys, cgi, datetime, urllib.parse, html, json

from sub_def.utils import error, print_html
from sub_def.file_ops import ensure_logfile, read_log, append_log
from sub_def.crypto import verify_csrf_token, generate_csrf_token, get_session

import conf

sys.stdout.reconfigure(encoding="utf-8")

Conf = conf.Conf

MESSAGE_COLORS = Conf["message_colors"]


def send_error(message, is_ajax=False):
    if is_ajax:
        print("Content-Type: application/json\r\n\r\n")
        print(json.dumps({"error": message}))
    else:
        error(message)

    sys.stdout.flush()
    sys.exit()


def handle_refresh(form, session):
    submitted_token = form.getvalue("csrf_token")
    if not verify_csrf_token(submitted_token, session):
        send_error("不正なリクエストです", True)
    print("Content-Type: application/json\r\n\r\n")
    print(json.dumps({"log": read_log(), "csrf_token": session["csrf_token"]}))
    sys.exit()


def handle_post(form, session):
    submitted_token = form.getvalue("csrf_token")

    if not verify_csrf_token(submitted_token, session):
        send_error(
            f"{submitted_token}不正なリクエストです{session}",
            form.getvalue("ajax") == "true",
        )

    if "bbs_txt" not in form or not form["bbs_txt"].value:
        send_error("発言を入力してください", form.getvalue("ajax") == "true")

    raw_txt = urllib.parse.unquote(form["bbs_txt"].value)
    if len(raw_txt) > 60:
        send_error("60文字以下でお願いします", form.getvalue("ajax") == "true")

    txt = "".join(c if c.isalnum() or c.isspace() else "-" for c in raw_txt[:60])
    txt = html.escape(txt)

    color = urllib.parse.unquote(form.getvalue("color", "#000000"))
    if not isinstance(color, str) or color not in MESSAGE_COLORS:
        color = "#000000"
    if not session.get("in_name"):
        send_error("ユーザー名が設定されていません", form.getvalue("ajax") == "true")

    time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    newlog = f"""<hr><font color="{color}"><b>{session["in_name"]}</b> > {txt} <font size="1">--{time}</font></font>\n"""
    append_log(newlog)

    csrf_token = generate_csrf_token(session)
    if form.getvalue("ajax") == "true":
        response = {"log": read_log(), "csrf_token": csrf_token}
        print("Content-Type: application/json\r\n\r\n")
        print(json.dumps(response))
        sys.stdout.flush()
        sys.exit()
    return csrf_token


def render_page(form, csrf_token):
    selected_color = form.getvalue("color", "#000000")
    content = {
        "log": read_log(),
        "colors": MESSAGE_COLORS,
        "selected_color": selected_color,
        "csrf_token": csrf_token,
    }

    print_html("bbs_tmp.html", content)


# メイン処理
session = get_session()
csrf_token = session.get("csrf_token") or generate_csrf_token(session)
FORM = cgi.FieldStorage()
ensure_logfile()

if FORM.getvalue("mode") == "refresh":
    handle_refresh(FORM, session)
elif "bbs_txt" in FORM:
    csrf_token = handle_post(FORM, session)
render_page(FORM, csrf_token)
