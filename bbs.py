#!D:\Python\Python314\python.exe

# bbs.py - 1行掲示板

import sys, cgi, datetime, html, json
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
        error(
            "不正なリクエストです",
        )

    # 修正: 余分な改行を防ぐ
    print("Content-Type: application/json\n")
    print(json.dumps({"log": read_log(), "csrf_token": session["csrf_token"]}))
    sys.exit()


def handle_post(form, session):
    submitted_token = form.get("csrf_token")
    raw_txt = form.get("bbs_txt", "")

    if not verify_csrf_token(submitted_token, session):
        error("不正なリクエストです", jump="my_page")

    if "bbs_txt" not in form or not raw_txt:
        error("発言を入力してください", jump="my_page")

    if not isinstance(raw_txt, str) or not raw_txt.strip():
        error("発言内容がありません", jump="my_page")

    if len(raw_txt) > 60:
        error("60文字以下でお願いします", jump="my_page")

    # 発言テキストの無毒化（空白を詰めてから60文字制限）
    txt = html.escape(raw_txt.strip()[:60])

    color = form.get("color", "#000000")
    if not isinstance(color, str) or color not in MESSAGE_COLORS:
        color = "#000000"

    if not session.get("in_name"):
        error("ユーザー名が設定されていません", jump="top")

    safe_name = html.escape(session["in_name"])

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # モダンなクラス構造でログを生成
    newlog = (
        f'<div class="bbs-line">'
        f'<span style="color: {color}; font-weight: bold;">{safe_name}</span> &gt; '
        f'{txt} <span class="bbs-time">--{timestamp}</span>'
        f"</div>\n"
    )
    append_log(newlog)

    csrf_token = generate_csrf_token(session)

    if form.get("ajax") == "true":
        response = {"log": read_log(), "csrf_token": csrf_token}
        print("Content-Type: application/json\n")
        print(json.dumps(response))
        sys.exit()

    return csrf_token


def render_page(form, csrf_token):
    selected_color = form.get("color", "#000000")

    if selected_color not in MESSAGE_COLORS:
        selected_color = "#000000"

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
    session = get_session()
    csrf_token = session.get("csrf_token") or generate_csrf_token(session)

    ensure_logfile()

    mode = FORM.get("mode")

    if mode == "refresh":
        handle_refresh(FORM, session)
    elif mode == "view":
        render_view_mode()
    elif "bbs_txt" in FORM:
        csrf_token = handle_post(FORM, session)
        render_page(FORM, csrf_token)
    else:
        render_page(FORM, csrf_token)
