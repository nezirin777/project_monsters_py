# utils.py

import sys
import os
import secrets
import logging
import json
import html
from jinja2 import Environment, FileSystemLoader

import conf

Conf = conf.Conf

sys.stdout.reconfigure(encoding="utf-8")

env = Environment(
    loader=FileSystemLoader("templates"), auto_reload=False, cache_size=100
)

# URLマッピングをモジュールレベルで定義
URL_MAP = {
    "top": (Conf["top_url"], {}),
    "kanri": (Conf["kanri_url"], {"mode": "KANRI"}),
    "my_page": (Conf["cgi_url"], {"mode": "my_page"}),
    "books": (Conf["cgi_url"], {"mode": "books"}),
    "medal_shop": (Conf["cgi_url"], {"mode": "medal_shop"}),
    "v_shop": (Conf["cgi_url"], {"mode": "v_shop"}),
    "v_shop2": (Conf["cgi_url"], {"mode": "v_shop2"}),
    "park": (Conf["cgi_url"], {"mode": "park"}),
    "omiai_room": (Conf["cgi_url"], {"mode": "omiai_room"}),
}

# 無限ループ検知用のグローバルフラグ
_IN_FLASH_AND_JUMP = False


# ==========#
# 共通関数  #
# ==========#
def is_ajax():
    return os.environ.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest"


def get_and_clear_flash(session):
    """
    セッションからフラッシュメッセージを取得し、即座に削除してクッキーを更新する。
    表示関数で一番最初に呼ぶことを想定。
    """
    if not isinstance(session, dict):
        return None, "error"

    flash_msg = session.pop("flash_msg", None)
    flash_type = session.pop("flash_type", "error")

    # フラッシュメッセージが存在した場合のみ、クッキーを1回更新
    if flash_msg is not None:
        try:
            from .crypto import set_session

            set_session(session)
        except Exception as e:
            logging.warning(f"Flash message clear failed: {e}")

    return flash_msg, flash_type


def _flash_and_jump(txt, msg_type="error", jump="top", log_level=logging.INFO):
    global _IN_FLASH_AND_JUMP
    from .crypto import get_session, set_session
    import urllib.parse

    # =========================================================
    # 0. サニタイズと安全なタグの復元
    # =========================================================
    sanitized_txt = html.escape(str(txt))
    # 許可する特定のタグだけ元に戻す（セキュリティと装飾の両立）
    allowed_tags = [
        "&lt;br&gt;",
        "&lt;span&gt;",
        "&lt;/span&gt;",
        "&lt;b&gt;",
        "&lt;/b&gt;",
    ]
    for tag in allowed_tags:
        sanitized_txt = sanitized_txt.replace(
            tag, tag.replace("&lt;", "<").replace("&gt;", ">")
        )

    # =========================================================
    # 1. 無限ループ防止（安全装置）
    # =========================================================
    if _IN_FLASH_AND_JUMP:
        logging.critical(f"無限ループ検知: {sanitized_txt}")
        print("Content-Type: text/plain; charset=utf-8\n")
        print(f"システムエラー: 無限ループ検知\n{sanitized_txt}")
        sys.exit()

    _IN_FLASH_AND_JUMP = True

    # =========================================================
    # 2. セッションの取得と更新
    # =========================================================
    try:
        session = get_session()
    except Exception:
        session = {}

    if session.get("flash_msg") and msg_type == "error":
        logging.warning(f"リダイレクト無限ループ回避: {session.get('flash_msg')}")
        jump = "99"

    token = secrets.token_hex(16)

    if jump in ("top", ""):
        session = dict(session)
        session["ref"] = "top"

    session.update(
        {
            "token": token,
            "flash_msg": sanitized_txt,  # サニタイズ済みの文字列を渡す
            "flash_type": msg_type,
        }
    )
    set_session(session)

    url, base_par = URL_MAP.get(jump, URL_MAP["my_page"])
    logging.log(log_level, f"{msg_type.upper()}: {sanitized_txt}, Jump: {jump}")

    # =========================================================
    # 3. 画面遷移（出力フェーズ）
    # =========================================================
    if is_ajax():
        # AJAX応答 (printの自動改行を考慮して \n は1つだけにする)
        print("Content-Type: application/json\n")
        print(
            json.dumps(
                {"ok": msg_type == "success", "msg": sanitized_txt, "type": msg_type}
            )
        )

    elif jump == "99":
        # 緊急テキスト表示モード
        print("Content-Type: text/plain; charset=utf-8\n")
        print(sanitized_txt)

    elif jump in ("top", ""):
        # GETリダイレクト（トップページへ）
        query = "?" + urllib.parse.urlencode(base_par) if base_par else ""
        print("Status: 302 Found")
        print(f"Location: {url}{query}")
        print("Content-Type: text/html; charset=utf-8\n")
        print(
            f'<html><head><meta http-equiv="refresh" content="0; url={url}{query}"></head><body></body></html>'
        )

    else:
        # 内部ディスパッチ（kanri または login へ）
        FORM = {"s": session, "mode": base_par.get("mode", ""), "token": token}

        if jump == "kanri":
            import kanri

            if hasattr(kanri, "FORM"):
                kanri.FORM["s"] = session
                kanri.FORM["token"] = token
            else:
                kanri.FORM = {"s": session, "token": token, "mode": "KANRI"}

            kanri.KANRI()
        else:
            from login import dispatch_function

            dispatch_function(FORM)

    sys.exit()


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


# ========#
# 情報    #
# ========#
def info(txt, jump="my_page"):
    _flash_and_jump(txt=txt, msg_type="info", jump=jump, log_level=logging.INFO)


# ==========#
# html出力  #
# ==========#
def print_html(tmp_name="", content={}):
    template = env.get_template(tmp_name)

    print("Content-Type: text/html; charset=utf-8\n")
    print(template.render(content))

    sys.exit()


# =============#
# 数値表記変換#
# =============#
UNITS = {
    1: {"threshold": "", "units": []},
    2: {"threshold": 1000, "units": ["", "k", "M", "G", "T", "P"]},
    3: {"threshold": 10000, "units": ["", "万", "億", "兆", "京"]},
}


def format_number(value, unit_type):
    if unit_type not in UNITS:
        return str(value)

    threshold = UNITS[unit_type]["threshold"]
    units = UNITS[unit_type]["units"]

    if unit_type == 1:
        return f"{value:,}"

    value = float(value)
    for unit in units:
        if value < threshold:
            return f"{value:.2f}".rstrip("0").rstrip(".") + unit
        value /= threshold
    return str(value)


def slim_number(item, unit_type=0):
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
    from .crypto import get_cookie

    cookie = get_cookie()
    try:
        unit_type = int(cookie.get("unit_type", 0))
    except (ValueError, TypeError):
        unit_type = 0

    return slim_number(item, unit_type)
