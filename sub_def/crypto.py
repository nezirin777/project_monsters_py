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

import conf
from .utils import error

Conf = conf.Conf
_cookie_cache = None


# ===========#
# 暗号化	#
# ===========#
def pass_encode(p: str) -> str:
    return base64.b64encode(hashlib.sha1(str(p).encode("utf-8")).digest()).decode()


def hash_password(password: str) -> str:
    """パスワードをSHA-256でハッシュ化する。ソルトを使用して強度を上げる。"""
    # 新しいソルトを生成
    salt = os.urandom(8)

    # ソルト + パスワードをハッシュ化
    hashed = hashlib.sha256(salt + password.encode("utf-8")).hexdigest()
    return f"{salt.hex()}:{hashed}"


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
        error(f"{name}の設定に失敗しました。", "top")


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
    """環境変数からクッキーデータを一度だけ取得しキャッシュ"""
    global _cookie_cache
    if _cookie_cache is None:
        _cookie_cache = os.environ.get("HTTP_COOKIE", "")
    return _cookie_cache


def get_cookie() -> Dict[str, str | int]:
    cookie: Dict[str, str | int] = {}
    raw_cookies = _get_raw_cookies()
    if raw_cookies:
        cook = cookies.SimpleCookie(raw_cookies)
        if cook.get("MONSTERS2"):
            try:
                pairs = urllib.parse.unquote_plus(cook["MONSTERS2"].value)
                decrypted = cryptocode.decrypt(pairs, Conf["secret_key"])
                if decrypted is None:
                    return cookie  # 復号化に失敗しても空の辞書を返す
                pairs = decrypted.split(",")
                for pair in pairs:
                    vale = pair.split(":")
                    if len(vale) == 2:  # "key:value"の形式を確認
                        key, value = vale
                        cookie[key] = int(value) if value.isdecimal() else value
            except Exception as e:
                error(f"クッキーの復号化に失敗しました: {e}", "top")
    return cookie


def get_session() -> Dict[str, str | int]:
    session: Dict[str, str | int] = {}
    raw_cookies = _get_raw_cookies()
    if not raw_cookies:
        error("セッションが取得できませんでした。", "top")
        return session
    cook = cookies.SimpleCookie(raw_cookies)
    if "session" not in cook:
        error("セッションが見つかりません。", "top")
        return session
    try:
        pairs = urllib.parse.unquote_plus(cook["session"].value)
        decrypted = cryptocode.decrypt(pairs, Conf["secret_key"])
        if decrypted is None:
            error("セッションの復号化に失敗しました。", "top")
            return session
        pairs = decrypted.split(",")
        if not pairs or (len(pairs) == 1 and not pairs[0]):  # 空のデータチェック
            error("セッションが空です。", "top")
            return session
        for pair in pairs:
            vale = pair.split(":")
            if len(vale) == 2:  # "key:value"の形式を確認
                key, value = vale
                session[key] = int(value) if value.isdecimal() else value
            else:
                error(f"セッションの処理中にエラーが発生しましたA: {pair}", "top")
    except Exception as e:
        error(f"セッションの処理中にエラーが発生しましたB: {e}", "top")
    return session


# =============#
# CSRFトークン  #
# =============#
def generate_csrf_token(cookie: dict) -> str:
    token = secrets.token_hex(16)
    cookie["csrf_token"] = token
    set_cookie(cookie)  # クッキーを即時保存
    return token


def verify_csrf_token(submitted_token: str, cookie: dict) -> bool:
    return submitted_token == cookie.get("csrf_token")
