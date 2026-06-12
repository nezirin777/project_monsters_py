#!D:\Python\Python314\python.exe

# bbs.py - 1行掲示板

import sys
import cgi
import datetime
import html
import json
from typing import NoReturn

import conf

# エントリポイントとして UTF-8 出力を強制する
sys.stdout.reconfigure(encoding="utf-8")

# フォームを辞書化
form = cgi.FieldStorage()
FORM = {key: form.getvalue(key) for key in form.keys()}

# パラメーターによるセーブデータフォルダ分岐処理
# ※ sub_def 系のインポートより先に apply_fol を実行する必要があるため
#   ここでフォーム解析と conf 初期化をまとめて行っている
conf.apply_fol(FORM)
Conf = conf.Conf

from sub_def.utils import error, print_html
from sub_def.file_ops import ensure_logfile, read_log, append_log
from sub_def.crypto import verify_csrf_token, generate_csrf_token, get_session

# BBS カラー選択肢の数。
# CSS で bbs-color-0 ～ bbs-color-{N-1} を定義しておくこと。
# フォームの value はインデックス文字列（"0", "1", ...）を使う。
BBS_COLOR_COUNT = 7


def _validate_color_index(value: str) -> int:
    """送信されたカラーインデックスを検証して int で返す。不正な値は 0 にフォールバック"""
    try:
        idx = int(value)
        if 0 <= idx < BBS_COLOR_COUNT:
            return idx
    except (TypeError, ValueError):
        pass
    return 0


def handle_refresh(form: dict, session: dict) -> NoReturn:
    """ログ更新リクエストを処理し、JSON レスポンスを返して終了する"""
    submitted_token = form.get("csrf_token")
    if not verify_csrf_token(submitted_token, session):
        error("不正なリクエストです")

    # CGI では print() が末尾に改行を付加するため、ヘッダー文字列に "\n" を含めることで
    # 「ヘッダー行 + 空行」の2つの改行を確保し、HTTP 仕様に沿った応答を生成する
    print("Content-Type: application/json\n")
    print(json.dumps({"log": read_log(), "csrf_token": session["csrf_token"]}))
    sys.exit()


def handle_post(form: dict, session: dict) -> int:
    """
    発言投稿リクエストを処理する。
    AJAX リクエストの場合は JSON を返して sys.exit()、
    通常リクエストの場合は次の render_page() で使う選択中カラーインデックスを返す。
    """
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

    color_idx = _validate_color_index(form.get("color", "0"))

    if not session.get("in_name"):
        error("ユーザー名が設定されていません", jump="top")

    safe_name = html.escape(session["in_name"])
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # カラーコードではなく CSS クラス名をログに埋め込む。
    # CSS 側でテーマごとに bbs-color-{n} の色を定義することで
    # ログファイルを書き直さずにテーマ対応できる。
    newlog = (
        f'<div class="bbs-line bbs-color-{color_idx}">'
        f'<span style="font-weight: bold;">{safe_name}</span> &gt; '
        f'{txt} <span class="bbs-time">--{timestamp}</span>'
        f"</div>\n"
    )
    append_log(newlog)

    csrf_token = generate_csrf_token(session)

    if form.get("ajax") == "true":
        response = {"log": read_log(), "csrf_token": csrf_token}
        # handle_refresh と同様、ヘッダー + 空行を確保するために "\n" を付加する
        print("Content-Type: application/json\n")
        print(json.dumps(response))
        sys.exit()

    return color_idx


def render_page(form: dict, csrf_token: str, selected_idx: int = 0) -> NoReturn:
    """通常の掲示板画面をレンダリングして終了する"""
    content = {
        "log": read_log(),
        # range をテンプレートに渡して bbs-color-0 ～ bbs-color-N のクラス名を生成させる
        "color_count": BBS_COLOR_COUNT,
        "selected_idx": selected_idx,
        "csrf_token": csrf_token,
        "Conf": Conf,
    }

    print_html("bbs_tmp.html", content)


def render_view_mode() -> NoReturn:
    """閲覧専用モード（ログのみ表示）をレンダリングして終了する"""
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
        selected_idx = handle_post(FORM, session)
        render_page(FORM, csrf_token, selected_idx)
    else:
        selected_idx = _validate_color_index(FORM.get("color", "0"))
        render_page(FORM, csrf_token, selected_idx)
