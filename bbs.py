#!D:\Python\Python312\python.exe
import sys, cgi, datetime, urllib.parse, html, json

from pathlib import Path
import conf
import sub_def
from sub_def.file_ops import ensure_logfile, read_log, append_log

sys.stdout.reconfigure(encoding="utf-8")

Conf = conf.Conf


# 設定クラス
class BBSConfig:
    DATADIR = Conf["savedir"]
    LOGFILE = Path(DATADIR) / "bbslog.log"
    MAX_LOG_LINES = Conf["max_log_lines"]
    MESSAGE_COLORS = Conf["message_colors"]


Config = BBSConfig()


def send_error(message, is_ajax=False):
    if is_ajax:
        print("Content-Type: application/json\r\n\r\n")
        print(json.dumps({"error": message}))
    else:
        sub_def.error(message)

    sys.stdout.flush()
    sys.exit()


def handle_refresh(form, cookie):
    submitted_token = form.getvalue("csrf_token")
    if not sub_def.verify_csrf_token(submitted_token, cookie):
        send_error("不正なリクエストです", True)
    print("Content-Type: application/json\r\n\r\n")
    print(
        json.dumps(
            {"log": read_log(Config.LOGFILE), "csrf_token": cookie["csrf_token"]}
        )
    )
    sys.exit()


def handle_post(form, cookie):
    submitted_token = form.getvalue("csrf_token")
    if not sub_def.verify_csrf_token(submitted_token, cookie):
        send_error("不正なリクエストです", form.getvalue("ajax") == "true")

    if "bbs_txt" not in form or not form["bbs_txt"].value:
        send_error("発言を入力してください", form.getvalue("ajax") == "true")
    raw_txt = urllib.parse.unquote(form["bbs_txt"].value)
    if len(raw_txt) > 60:
        send_error("60文字以下でお願いします", form.getvalue("ajax") == "true")
    txt = "".join(c if c.isalnum() or c.isspace() else "-" for c in raw_txt[:60])
    txt = html.escape(txt)

    color = urllib.parse.unquote(form.getvalue("color", "#000000"))
    if not isinstance(color, str) or color not in Config.MESSAGE_COLORS:
        color = "#000000"
    if not cookie.get("in_name"):
        send_error("ユーザー名が設定されていません", form.getvalue("ajax") == "true")

    time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    newlog = f"""<hr><font color="{color}"><b>{cookie["in_name"]}</b> > {txt} <font size="1">--{time}</font></font>\n"""
    append_log(Config.LOGFILE, newlog, Config.MAX_LOG_LINES)

    csrf_token = sub_def.generate_csrf_token(cookie)
    if form.getvalue("ajax") == "true":
        response = {"log": read_log(Config.LOGFILE), "csrf_token": csrf_token}
        print("Content-Type: application/json\r\n\r\n")
        print(json.dumps(response))
        sys.stdout.flush()
        sys.exit()
    return csrf_token


def render_page(form, csrf_token):
    selected_color = form.getvalue("color", "#000000")
    content = {
        "Conf": Conf,
        "log": read_log(Config.LOGFILE),
        "colors": Config.MESSAGE_COLORS,
        "selected_color": selected_color,
        "csrf_token": csrf_token,
    }

    sub_def.print_html("bbs_tmp.html", content)


# メイン処理
cookie = sub_def.get_cookie()
csrf_token = cookie.get("csrf_token") or sub_def.generate_csrf_token(cookie)
FORM = cgi.FieldStorage()
ensure_logfile(Config.LOGFILE)

if FORM.getvalue("mode") == "refresh":
    handle_refresh(FORM, cookie)
elif "bbs_txt" in FORM:
    csrf_token = handle_post(FORM, cookie)
render_page(FORM, csrf_token)
