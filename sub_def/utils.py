# utils.py

import sys
import secrets
import logging
import html  # 追加: エラーメッセージのサニタイズ用
from jinja2 import Environment, FileSystemLoader


import conf

sys.stdout.reconfigure(encoding="utf-8")

Conf = conf.Conf

# ログ設定（UTF-8で保存）
logging.basicConfig(
    filename="app.log",
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8",
)

env = Environment(loader=FileSystemLoader("templates"))

# URLマッピングをモジュールレベルで定義
URL_MAP = {
    "top": (Conf["top_url"], {}),
    "kanri": (Conf["kanri_url"], {"mode": "KANRI"}),
    "": (Conf["cgi_url"], {"mode": "my_page"}),
}


# ========#
# エラー  #
# ========#
def error(txt, jump="", log_level=logging.ERROR):
    from .crypto import get_session, set_session

    token = secrets.token_hex(16)
    session = get_session() if jump != "top" else {}
    session |= {"token": token}
    set_session(session)

    # エラーメッセージをサニタイズ
    sanitized_txt = html.escape(str(txt))

    # URLとパラメータを取得（jumpがURL_MAPにない場合はデフォルト）
    url, base_par = URL_MAP.get(jump, URL_MAP[""])
    par = base_par | {"token": token} if jump != "top" else base_par

    logging.log(log_level, f"Error: {sanitized_txt}, Jump: {jump}")

    content = {
        "Conf": Conf,
        "txt": sanitized_txt,
        "url": url,
        "par": par,
        "jump": jump,  # 条件分岐用にjumpも渡す
    }

    print_html("error_tmp.html", content)


# ==========#
# リザルト #
# ==========#
def print_result(txt="", html="", token="", kanri=False):
    content = {
        "Conf": Conf,
        "txt": txt,
        "html": html,
        "token": token,
        "kanri": kanri,
    }

    print_html("result_tmp.html", content)


# ==========#
# html出力  #
# ==========#
def print_html(tmp_name="", content={}, exit=True):
    template = env.get_template(tmp_name)
    full_content = content or {}  # contentがNoneの場合、空の辞書を使用

    print("Content-Type: text/html; charset=utf-8\r\n\r\n")
    print(template.render(full_content))

    if exit:
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
