# crypto.py

import os
import hashlib
import base64
import cryptocode
import urllib.parse
from http import cookies
import datetime
import secrets
from typing import Dict

from .utils import error
import conf

Conf = conf.Conf


# ===========#
# 暗号化	#
# ===========#
def pass_encode(p: str) -> str:
    return base64.b64encode(hashlib.sha1(str(p).encode("utf-8")).digest()).decode()


def hash_password(password: str) -> str:
    """パスワードをSHA-256でハッシュ化する。ソルトを使用して強度を上げる。"""
    try:
        # 新しいソルトを生成
        salt = os.urandom(8)

        # ソルト + パスワードをハッシュ化
        hashed = hashlib.sha256(salt + password.encode("utf-8")).hexdigest()
        return f"{salt.hex()}:{hashed}"
    except Exception as e:
        error(f"パスワードハッシュ化エラー: {e}", "top")


def verify_password(password: str, stored_hash: str) -> bool:
    """入力パスワードが保存されたハッシュと一致するか検証する。"""
    salt, hashed = stored_hash.split(":")
    salt = bytes.fromhex(salt)
    # 入力パスワードを再ハッシュ
    return hashed == hashlib.sha256(salt + password.encode("utf-8")).hexdigest()


# =============#
# クッキーSET #
# =============#
def _set_cookie_common(
    cookie, name: str, data: dict, expires_delta: datetime.timedelta, path: str = "/"
) -> None:

    try:
        cookie = cookies.SimpleCookie()
        cook = ",".join([f"{k}:{v}" for k, v in data.items()])
        cook = cryptocode.encrypt(cook, Conf["secret_key"])
        cookie[name] = urllib.parse.quote_plus(cook)
        cookie[name]["path"] = path
        # UTCじゃないとブラウザ保存時にローカル時間にさらにタイムゾーンが追加される
        expires = datetime.datetime.now(datetime.timezone.utc) + expires_delta
        cookie[name]["expires"] = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")
        cookie[name]["SameSite"] = "Strict"
        print(cookie)
    except Exception as e:
        error(f"クッキー {name} の設定に失敗しました: {e}", "top")


def set_cookie(c_data: dict) -> None:
    cookie = cookies.SimpleCookie()
    _set_cookie_common(cookie, "MONSTERS2", c_data, datetime.timedelta(days=60))


def set_session(data: dict = None) -> None:
    cookie = cookies.SimpleCookie()
    _set_cookie_common(cookie, "session", data, datetime.timedelta(minutes=30))


# =============#
# クッキーGET #
# =============#
def _get_raw_cookies() -> str:
    """環境変数からクッキーデータを取得"""
    return os.environ.get("HTTP_COOKIE", "")


def _parse_cookie(raw_cookies: str, name: str) -> Dict[str, str | int]:
    """指定されたクッキーをパースして辞書を返す"""
    result: Dict[str, str | int] = {}
    if not raw_cookies:
        return result
    try:
        cook = cookies.SimpleCookie(raw_cookies)
        if name in cook:
            pairs = urllib.parse.unquote_plus(cook[name].value)
            decrypted = cryptocode.decrypt(pairs, Conf["secret_key"])

            if decrypted is None:
                error(f"クッキー {name} の復号化に失敗しました", "top")

            for pair in decrypted.split(","):
                if ":" in pair:
                    key, value = pair.split(":", 1)
                    result[key] = int(value) if value.isdecimal() else value
    except Exception as e:
        error(
            f"クッキー {name} の処理中にエラーが発生しました: {e}",
            "top",
        )
    return result


def get_cookie() -> Dict[str, str | int]:
    return _parse_cookie(_get_raw_cookies(), "MONSTERS2")


def get_session() -> Dict[str, str | int]:
    return _parse_cookie(_get_raw_cookies(), "session")


# =============#
# CSRFトークン  #
# =============#
def generate_csrf_token(session: dict) -> str:
    token = secrets.token_hex(16)
    session["csrf_token"] = token
    set_session(session)  # クッキーを即時保存
    return token


def verify_csrf_token(submitted_token: str, session: dict) -> bool:
    return secrets.compare_digest(submitted_token or "", session.get("csrf_token", ""))


def token_check(FORM, session):
    form_token = FORM.get("token", "")
    session_token = session.get("token", "")

    if not form_token or not secrets.compare_digest(session_token, form_token):
        error("無効なセッションです。再度お試しください")

    session.update(
        {
            "ref": "",
            "token": secrets.token_hex(16),
            "in_name": session.get("in_name", FORM.get("name", "")),
        }
    )
    set_session(session)

    return session
