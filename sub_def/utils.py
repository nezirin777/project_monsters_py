# utils.py

import sys
import os
import secrets
import logging
import json
import html
import urllib.parse
from typing import Any, NoReturn

from jinja2 import Environment, FileSystemLoader

import conf

Conf = conf.Conf

# sys.stdout.reconfigure はライブラリモジュールには不要。
# CGI エントリポイント（login.py / monster.py 等）で設定済みのため削除。

env = Environment(
    loader=FileSystemLoader("templates"), auto_reload=False, cache_size=100
)

# 遷移先 URL とデフォルトパラメータのマッピング。
# "99" はテキスト緊急表示モード（ループ回避用）のため意図的に含めない。
URL_MAP: dict[str, tuple[str, dict]] = {
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

# -------------------------------------------------------
# 無限ループ検知フラグ
# sys.exit() は SystemExit を raise するため、finally ブロック経由で
# error() が再帰的に呼ばれるリスクがある。このフラグで二重実行を防ぐ。
# CGI は 1 リクエスト 1 プロセスなので、フラグはリクエスト内でのみ有効。
# -------------------------------------------------------
_IN_FLASH_AND_JUMP: bool = False


# ==========#
# 共通関数  #
# ==========#
def is_ajax() -> bool:
    """現在のリクエストが XMLHttpRequest（AJAX）かどうかを返す"""
    return os.environ.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest"


def get_and_clear_flash(session: dict) -> tuple[str | None, str]:
    """
    セッションからフラッシュメッセージを取り出してクリアし、クッキーを更新する。
    表示ハンドラの冒頭で必ず 1 回だけ呼ぶこと。

    Returns:
        (flash_msg, flash_type) — メッセージがない場合は (None, "error")
    """
    if not isinstance(session, dict):
        return None, "error"

    flash_msg = session.pop("flash_msg", None)
    flash_type = session.pop("flash_type", "error")

    # フラッシュが存在した場合のみセッションクッキーを更新する
    if flash_msg is not None:
        try:
            # crypto → utils の循環インポートを避けるため関数内でインポートする
            from .crypto import set_session

            set_session(session)
        except Exception as e:
            logging.warning(f"Flash message clear failed: {e}")

    return flash_msg, flash_type


def _flash_and_jump(
    txt: str,
    msg_type: str = "error",
    jump: str = "top",
    log_level: int = logging.INFO,
) -> NoReturn:
    """
    メッセージをセッションに保存して指定先へ遷移し、sys.exit() で終了する。

    遷移パターン:
        "top" / ""  → 302 GET リダイレクト（ログインセッションをリセット）
        "99"        → テキスト緊急表示（ループ回避時のフォールバック）
        "kanri"     → kanri.KANRI() を内部ディスパッチ
        その他      → login.dispatch_function() を内部ディスパッチ
    """
    global _IN_FLASH_AND_JUMP

    # =========================================================
    # 0. サニタイズ
    #    html.escape() で全タグを無毒化した後、許可リストのタグだけ復元する。
    #    属性付きタグ（例: <span style="...">）はエスケープされたまま残るため
    #    XSS は起こらない。
    # =========================================================
    sanitized_txt = html.escape(str(txt))
    _ALLOWED_TAGS = ["<br>", "<span>", "</span>", "<b>", "</b>"]
    for tag in _ALLOWED_TAGS:
        sanitized_txt = sanitized_txt.replace(html.escape(tag), tag)

    # =========================================================
    # 1. 無限ループ防止
    #    sys.exit() が SystemExit を送出するため、finally 経由で
    #    再入することがある。フラグで検知して緊急テキスト表示にフォールバック。
    # =========================================================
    if _IN_FLASH_AND_JUMP:
        logging.critical(f"無限ループ検知: {sanitized_txt}")
        print("Content-Type: text/plain; charset=utf-8\n")
        print(f"システムエラー: 無限ループ検知\n{sanitized_txt}")
        sys.exit()

    _IN_FLASH_AND_JUMP = True

    # =========================================================
    # 2. セッション更新
    # =========================================================
    # crypto → utils の循環インポートを避けるため関数内でインポートする
    from .crypto import get_session, set_session

    try:
        session = get_session()
    except Exception:
        session = {}

    # 直前の flash_msg が残っていれば無限リダイレクトが起きているとみなす
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
            "flash_msg": sanitized_txt,
            "flash_type": msg_type,
        }
    )
    set_session(session)

    # "99" は URL_MAP にない特殊値なので lookup 対象外とする
    _SPECIAL_JUMPS = {"99", "top", ""}
    if jump not in URL_MAP and jump not in _SPECIAL_JUMPS:
        logging.warning(f"未定義のjump先: {jump}, my_page へ fallback")

    url, base_par = URL_MAP.get(jump, URL_MAP["my_page"])
    logging.log(log_level, f"{msg_type.upper()}: {sanitized_txt}, Jump: {jump}")

    # =========================================================
    # 3. 画面遷移
    # =========================================================
    if is_ajax():
        # AJAX レスポンス（ヘッダー末尾の空行は print の自動改行で補完される）
        print("Content-Type: application/json\n")
        print(
            json.dumps(
                {"ok": msg_type == "success", "msg": sanitized_txt, "type": msg_type}
            )
        )

    elif jump == "99":
        # 緊急テキスト表示モード（ループ回避フォールバック）
        print("Content-Type: text/plain; charset=utf-8\n")
        print(sanitized_txt)

    elif jump in ("top", ""):
        # GET リダイレクト（ログインセッションをリセットしてトップへ）
        query = "?" + urllib.parse.urlencode(base_par) if base_par else ""
        print("Status: 302 Found")
        print(f"Location: {url}{query}")
        print("Content-Type: text/html; charset=utf-8\n")
        print(
            f"<html><head>"
            f'<meta http-equiv="refresh" content="0; url={url}{query}">'
            f"</head><body></body></html>"
        )

    else:
        # 内部ディスパッチ
        # kanri / login は循環インポートを避けるため関数内でインポートする
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
# ログ設定     #
# ==============#
def configure_logging(level: int = logging.ERROR) -> None:
    """
    ファイルへの基本ログ設定を行う。
    basicConfig は初回呼び出しのみ有効（以降は no-op）。
    """
    logging.basicConfig(
        filename="app.log",
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        encoding="utf-8",
    )


configure_logging()


# ==============================#
# 公開インターフェース           #
# ==============================#
def error(txt: Any, jump: str = "my_page", log_level: int = logging.ERROR) -> NoReturn:
    """エラーメッセージをフラッシュしてリダイレクトする。必ず sys.exit() で終了する"""
    _flash_and_jump(txt=txt, msg_type="error", jump=jump, log_level=log_level)


def success(txt: Any, jump: str = "my_page") -> NoReturn:
    """成功メッセージをフラッシュしてリダイレクトする。必ず sys.exit() で終了する"""
    _flash_and_jump(txt=txt, msg_type="success", jump=jump, log_level=logging.INFO)


def info(txt: Any, jump: str = "my_page") -> NoReturn:
    """情報メッセージをフラッシュしてリダイレクトする。必ず sys.exit() で終了する"""
    _flash_and_jump(txt=txt, msg_type="info", jump=jump, log_level=logging.INFO)


# ==========#
# HTML 出力 #
# ==========#
def print_html(tmp_name: str = "", content: dict | None = None) -> NoReturn:
    """
    Jinja2 テンプレートをレンダリングして HTTP レスポンスとして出力し、終了する。

    Note:
        content のデフォルトを {} にすると Python のミュータブルデフォルト引数の
        罠にはまるため None を使う。
    """
    template = env.get_template(tmp_name)
    print("Content-Type: text/html; charset=utf-8\n")
    print(template.render(content or {}))
    sys.exit()


# =============#
# 数値表記変換 #
# =============#

# unit_type ごとの変換設定。
# type 1 はカンマ区切りのみなので threshold は使わない（None で明示）。
UNITS: dict[int, dict] = {
    1: {"threshold": None, "units": []},
    2: {"threshold": 1000, "units": ["", "k", "M", "G", "T", "P"]},
    3: {"threshold": 10000, "units": ["", "万", "億", "兆", "京"]},
}


def format_number(value: int | float, unit_type: int) -> str:
    """数値を unit_type に応じた表記文字列に変換する"""
    if unit_type not in UNITS:
        return str(value)

    # type 1 はカンマ区切りのみ（threshold / units は使わない）
    if unit_type == 1:
        return f"{value:,}"

    threshold = UNITS[unit_type]["threshold"]
    units = UNITS[unit_type]["units"]

    val = float(value)
    for unit in units:
        if val < threshold:
            return f"{val:.2f}".rstrip("0").rstrip(".") + unit
        val /= threshold
    return str(val)


def slim_number(item: Any, unit_type: int = 0) -> Any:
    """
    item 内の数値を unit_type に応じて再帰的に変換する。
    unit_type=0 の場合は変換なしでそのまま返す。
    """
    if unit_type == 0:
        return item

    if isinstance(item, (int, float)):
        return format_number(item, unit_type)

    if isinstance(item, dict):
        return {k: slim_number(v, unit_type) for k, v in item.items()}

    if isinstance(item, list):
        return [slim_number(v, unit_type) for v in item]

    # 文字列の場合: 純粋な正の整数表現のみ変換する（負数・小数は対象外）
    return format_number(int(item), unit_type) if str(item).isdecimal() else item


def slim_number_with_cookie(item: Any) -> Any:
    """
    クッキーの unit_type 設定を読み取り、slim_number() を適用して返す。
    クッキー取得 / パースに失敗した場合は変換なし（unit_type=0）にフォールバック。
    """
    # crypto → utils の循環インポートを避けるため関数内でインポートする
    from .crypto import get_cookie

    cookie = get_cookie()
    try:
        unit_type = int(cookie.get("unit_type", 0))
    except (ValueError, TypeError):
        unit_type = 0

    return slim_number(item, unit_type)
