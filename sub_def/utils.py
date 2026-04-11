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
    "my_page": (Conf["cgi_url"], {"mode": "my_page"}),
    "books": (Conf["cgi_url"], {"mode": "books"}),
}


# ==========#
# 共通関数  #
# ==========#
def is_ajax():
    return os.environ.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest"


def clear_flash():
    from .crypto import get_session, set_session

    """表示済みのflashメッセージをセッションから削除する"""
    session = get_session()
    if "flash_msg" in session or "flash_type" in session:
        session.pop("flash_msg", None)
        session.pop("flash_type", None)
        set_session(session)  # ← ここで即座にクッキー更新


def _flash_and_jump(txt, msg_type="error", jump="my_page", log_level=logging.INFO):
    from .crypto import get_session, set_session

    token = secrets.token_hex(16)
    session = get_session() if jump != "top" else {}

    # ★ flash統一
    session |= {
        "token": token,
        "flash_msg": str(txt),
        "flash_type": msg_type,
    }

    set_session(session)

    sanitized_txt = html.escape(str(txt))
    url, base_par = URL_MAP.get(jump, URL_MAP["my_page"])
    par = base_par | {"token": token} if jump != "top" else base_par

    logging.log(log_level, f"{msg_type.upper()}: {sanitized_txt}, Jump: {jump}")

    # AJAX
    if is_ajax():
        print("Content-Type: application/json\r\n\r\n")
        print(
            json.dumps(
                {"ok": msg_type == "success", "msg": sanitized_txt, "type": msg_type}
            )
        )
        sys.exit()

    # 指定されたモードに移行
    if not jump == "":
        from login import dispatch_function

        FORM = {
            "s": session,
            "mode": base_par["mode"],
            "token": session.get("token"),
        }
        dispatch_function(FORM)
        sys.exit()

    content = {
        "Conf": Conf,
        "txt": sanitized_txt,
        "url": url,
        "par": par,
        "jump": jump,
    }

    print_html("error_tmp.html", content)


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
def error(txt, jump="my_page", log_level=logging.ERROR):
    _flash_and_jump(txt=txt, msg_type="error", jump=jump, log_level=log_level)


# ========#
# 成功    #
# ========#
def success(txt, jump="my_page"):
    _flash_and_jump(txt=txt, msg_type="success", jump=jump, log_level=logging.INFO)


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
def print_html(tmp_name="", content={}, exit=True):
    clear_flash()

    template = env.get_template(tmp_name)

    print("Content-Type: text/html; charset=utf-8\n")
    print(template.render(content))

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
