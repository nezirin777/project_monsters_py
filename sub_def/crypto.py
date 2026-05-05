# crypto.py

import base64
from Cryptodome.Cipher import AES
import datetime
import hashlib
import os
import secrets
import urllib.parse
from http import cookies
from typing import Dict, Any
import logging

import conf

Conf = conf.Conf

_cookie_cache = None
_session_cache = None


# ------------------- ヘルパー関数 -------------------
def _encrypt_cookie_value(data: str, secret_key: str) -> str:
    """クッキー暗号化"""
    key = hashlib.sha256(secret_key.encode("utf-8")).digest()
    cipher = AES.new(key, AES.MODE_GCM)
    ciphertext, tag = cipher.encrypt_and_digest(data.encode("utf-8"))
    encrypted = cipher.nonce + ciphertext + tag
    return base64.urlsafe_b64encode(encrypted).decode("utf-8")


def _decrypt_cookie_value(encrypted_b64: str, secret_key: str) -> str:
    """クッキー復号"""
    key = hashlib.sha256(secret_key.encode("utf-8")).digest()
    data = base64.urlsafe_b64decode(encrypted_b64)
    nonce = data[:16]
    ciphertext = data[16:-16]
    tag = data[-16:]
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    plaintext = cipher.decrypt_and_verify(ciphertext, tag)
    return plaintext.decode("utf-8")


# ===========#
# 暗号化     #
# ===========#
def pass_encode(p: str) -> str:
    return base64.b64encode(hashlib.sha1(str(p).encode("utf-8")).digest()).decode()


def hash_password(password: str) -> str:
    """パスワードをSHA-256でハッシュ化（ソルト付き）"""
    try:
        salt = os.urandom(8)
        hashed = hashlib.sha256(salt + password.encode("utf-8")).hexdigest()
        return f"{salt.hex()}:{hashed}"
    except Exception as e:
        # 無限ループ回避のため、error()ではなく例外をスロー
        logging.error(f"パスワードハッシュ化エラー: {e}")
        raise RuntimeError("パスワードの処理に失敗しました。")


def verify_password(password: str, stored_hash: str) -> bool:
    """入力パスワードが保存されたハッシュと一致するか検証"""
    try:
        salt_hex, hashed = stored_hash.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        return hashed == hashlib.sha256(salt + password.encode("utf-8")).hexdigest()
    except Exception as e:
        logging.error(f"パスワード検証エラー: {e}")
        return False


# =============#
# クッキーSET  #
# =============#
def _is_secure_request() -> bool:
    """現在のリクエストがHTTPSかどうかを判定"""
    if os.environ.get("HTTPS", "").lower() in {"on", "1", "true"}:
        return True
    if os.environ.get("REQUEST_SCHEME", "").lower() == "https":
        return True
    if os.environ.get("HTTP_X_FORWARDED_PROTO", "").lower() == "https":
        return True
    return False


def _set_cookie_common(
    name: str,
    data: dict,
    expires_delta: datetime.timedelta,
    path: str = "/",
) -> None:
    try:
        # dictの値をすべて文字列化して結合
        cook = ",".join([f"{k}:{str(v)}" for k, v in data.items()])
        encrypted_cook = _encrypt_cookie_value(cook, Conf["secret_key"])

        cookie = cookies.SimpleCookie()
        cookie[name] = urllib.parse.quote_plus(encrypted_cook)
        cookie[name]["path"] = path

        expires = datetime.datetime.now(datetime.timezone.utc) + expires_delta
        cookie[name]["expires"] = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")
        cookie[name]["SameSite"] = "Strict"
        cookie[name]["httponly"] = True

        if _is_secure_request():
            cookie[name]["secure"] = True

        print(cookie)
    except Exception as e:
        # error()の使用を避け、システムエラーとして記録
        logging.error(f"クッキー {name} の設定に失敗しました: {e}")


def set_cookie(c_data: dict) -> None:
    global _cookie_cache
    c_data = dict(c_data)
    c_data["expires_at"] = (
        datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=46)
    ).isoformat()
    _cookie_cache = c_data
    _set_cookie_common("MONSTERS2", c_data, datetime.timedelta(days=60))


def set_session(data: dict = None) -> None:
    global _session_cache
    data = dict(data or {})
    data["expires_at"] = (
        datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=30)
    ).isoformat()
    _session_cache = data
    _set_cookie_common("session", data, datetime.timedelta(minutes=30))


# =============#
# クッキーGET  #
# =============#
def _get_raw_cookies() -> str:
    return os.environ.get("HTTP_COOKIE", "")


def _parse_cookie(raw_cookies: str, name: str) -> Dict[str, str]:
    """指定されたクッキーをパースして辞書を返す"""
    result = {}
    if not raw_cookies:
        return result

    try:
        cook = cookies.SimpleCookie(raw_cookies)
        if name not in cook:
            return result

        encrypted_value = urllib.parse.unquote_plus(cook[name].value)
        decrypted = _decrypt_cookie_value(encrypted_value, Conf["secret_key"])

        if not decrypted or not isinstance(decrypted, str) or ":" not in decrypted:
            return {}

        for pair in decrypted.split(","):
            pair = pair.strip()
            if ":" in pair:
                try:
                    key, value = pair.split(":", 1)
                    result[key.strip()] = value.strip()
                except Exception:
                    continue

    except Exception as e:
        logging.warning(f"Cookie parse exception for {name}: {e}")
        return {}

    return result


def _is_expired(data: dict) -> bool:
    """データ内の expires_at が現在時刻を過ぎているか判定"""
    if "expires_at" not in data:
        return True
    try:
        expires_at = datetime.datetime.fromisoformat(data["expires_at"])
        return expires_at < datetime.datetime.now(datetime.timezone.utc)
    except Exception:
        return True


def get_cookie() -> Dict[str, str]:
    global _cookie_cache
    if _cookie_cache is not None:
        return _cookie_cache

    cookie = _parse_cookie(_get_raw_cookies(), "MONSTERS2")

    # クッキー側の有効期限も厳密にチェックする
    if not cookie or _is_expired(cookie):
        _cookie_cache = {}
        return _cookie_cache

    _cookie_cache = cookie
    return cookie


def get_session() -> Dict[str, str]:
    global _session_cache
    if _session_cache is not None:
        return _session_cache

    session = _parse_cookie(_get_raw_cookies(), "session")

    # 期限チェックロジックを共通関数に切り出してスッキリ
    if not session or _is_expired(session):
        _session_cache = {}
        return _session_cache

    _session_cache = session
    return session


# =============#
# CSRFトークン #
# =============#
def generate_csrf_token(session: dict) -> str:
    token = secrets.token_hex(16)
    session["csrf_token"] = token
    set_session(session)
    return token


def verify_csrf_token(submitted_token: str, session: dict) -> bool:
    return secrets.compare_digest(submitted_token or "", session.get("csrf_token", ""))


def token_check(FORM: dict, session: dict, login_data: dict = None) -> dict:
    form_token = FORM.get("token", "").strip()
    session_token = session.get("token", "").strip()

    if not form_token or not secrets.compare_digest(session_token, form_token):
        # ここは直接的なユーザー入力チェックなので error(flash_and_jump) で問題なし
        from .utils import error

        # error("無効なセッションです。再度お試しください", "")

    session.update(
        {
            "ref": "",
            "token": secrets.token_hex(16),
        }
    )

    if login_data:
        session.update(login_data)
    elif not session.get("in_name"):
        session["in_name"] = FORM.get("user_name", "")

    set_session(session)
    return session
