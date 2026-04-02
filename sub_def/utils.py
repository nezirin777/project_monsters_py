# utils.py

import sys
import os
import secrets
import logging
import json
import html  # 追加: エラーメッセージのサニタイズ用
from jinja2 import Environment, FileSystemLoader


import conf

sys.stdout.reconfigure(encoding="utf-8")

Conf = conf.Conf

env = Environment(
    loader=FileSystemLoader("templates"), auto_reload=False, cache_size=100
)

# URLマッピングをモジュールレベルで定義
URL_MAP = {
    "top": (Conf["top_url"], {}),
    "kanri": (Conf["kanri_url"], {"mode": "KANRI"}),
    "": (Conf["cgi_url"], {"mode": "my_page"}),
}


# ==============#
# エラーログ設定 #
# ==============#
def configure_logging(level=logging.ERROR):
    logging.basicConfig(
        filename="app.log",
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        encoding="utf-8",
    )


# 初期化時にデフォルトでERRORレベルを設定
configure_logging()


# ========#
# エラー  #
# ========#
def is_ajax():
    return os.environ.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest"


def error(txt, jump="", log_level=logging.ERROR, exit_code=0):
    from .crypto import get_session, set_session

    token = secrets.token_hex(16)
    session = get_session() if jump != "top" else {}
    session |= {"token": token}
    set_session(session)

    sanitized_txt = html.escape(str(txt))
    url, base_par = URL_MAP.get(jump, URL_MAP[""])
    par = base_par | {"token": token} if jump != "top" else base_par

    logging.log(log_level, f"Error: {sanitized_txt}, Jump: {jump}")

    if is_ajax():  # AJAXの場合
        print("Content-Type: application/json\r\n\r\n")
        print(json.dumps({"ok": False, "error": sanitized_txt}))
    else:
        content = {
            "Conf": Conf,
            "txt": sanitized_txt,
            "url": url,
            "par": par,
            "jump": jump,
        }

        print_html("error_tmp.html", content)


# ==========#
# リザルト #
# ==========#
def print_result(content, kanri=False):
    content.update(
        {
            "kanri": kanri,
        }
    )

    print_html("result_tmp.html", content)


# ==========#
# html出力  #
# ==========#
def print_html(tmp_name="", content=None, exit=True):
    template = env.get_template(tmp_name)
    full_content = content or {}  # contentがNoneの場合、空の辞書を使用

    print("Content-Type: text/html; charset=utf-8\n")
    print(template.render(full_content))

    if exit:
        sys.exit()


# ==========#
# json出力  #
# ==========#
def print_json(data):
    print("Content-Type: application/json\r\n\r\n")
    print(json.dumps(data))
    sys.exit()


# =============#
# 数値表記変換#
# =============#
# 単位変換の定数
UNITS = {
    1: {"threshold": "", "units": []},
    2: {"threshold": 1000, "units": ["", "K", "M", "G", "T", "P"]},
    3: {"threshold": 10000, "units": ["", "万", "億", "兆", "京"]},
}


def format_number(value, unit_type):
    """数値を指定された単位形式に変換"""
    if unit_type not in UNITS:
        return str(value)

    threshold = UNITS[unit_type]["threshold"]
    units = UNITS[unit_type]["units"]

    if unit_type == 1:  # カンマ区切り
        return f"{value:,}"

    value = float(value)
    for unit in units:
        if value < threshold:
            return f"{value:.2f}".rstrip("0").rstrip(".") + unit
        value /= threshold
    return str(value)


def slim_number(item, unit_type=0):
    """数値やデータ構造を指定された形式に変換"""
    if unit_type == 0:
        return item

    if isinstance(item, (int, float)):
        return format_number(item, unit_type)

    if isinstance(item, dict):
        return {k: slim_number(v, unit_type) for k, v in item.items()}

    if isinstance(item, list):
        return [slim_number(v, unit_type) for v in item]

    return item if not str(item).isdecimal() else format_number(int(item), unit_type)


def slim_number_with_cookie(item):
    """クッキーから単位タイプを取得してslim_numberを適用"""
    from .crypto import get_cookie

    cookie = get_cookie()
    unit_type = cookie.get("unit_type", 0)
    return slim_number(item, unit_type)
