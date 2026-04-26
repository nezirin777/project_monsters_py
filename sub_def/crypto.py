# crypto.py

import base64
from Cryptodome.Cipher import AES
import datetime
import hashlib
import os
import sys
import secrets
import urllib.parse
from http import cookies
from typing import Dict

from .utils import error

import conf

Conf = conf.Conf


# ------------------- ヘルパー関数（crypto.py などに置く） -------------------
def _encrypt_cookie_value(data: str, secret_key: str) -> str:
    """クッキー暗号化 - secret_key が短くてもOK（SHA-256で32バイトに変換）"""
    # secret_key をそのまま使って32バイトの鍵に変換（これが一番シンプルで安全）
    key = hashlib.sha256(secret_key.encode("utf-8")).digest()

    cipher = AES.new(key, AES.MODE_GCM)
    ciphertext, tag = cipher.encrypt_and_digest(data.encode("utf-8"))

    # nonce + ciphertext + tag を結合して urlsafe base64
    encrypted = cipher.nonce + ciphertext + tag
    return base64.urlsafe_b64encode(encrypted).decode("utf-8")


def _decrypt_cookie_value(encrypted_b64: str, secret_key: str) -> str:
    """復号（同じくSHA-256で鍵生成）"""
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
# クッキーSET  #
# =============#
def _is_secure_request() -> bool:
    """現在のリクエストがHTTPSかどうかを判定"""
    https = os.environ.get("HTTPS", "").lower()
    if https in {"on", "1", "true"}:
        return True

    request_scheme = os.environ.get("REQUEST_SCHEME", "").lower()
    if request_scheme == "https":
        return True

    forwarded_proto = os.environ.get("HTTP_X_FORWARDED_PROTO", "").lower()
    if forwarded_proto == "https":
        return True

    return False


def _set_cookie_common(
    name: str,
    data: dict,
    expires_delta: datetime.timedelta,
    path: str = "/",
) -> None:
    try:
        # dict → 文字列に変換
        cook = ",".join([f"{k}:{v}" for k, v in data.items()])

        # 暗号化（secret_key をそのまま渡すだけ）
        encrypted_cook = _encrypt_cookie_value(cook, Conf["secret_key"])

        cookie = cookies.SimpleCookie()
        cookie[name] = urllib.parse.quote_plus(encrypted_cook)
        cookie[name]["path"] = path

        # UTCじゃないとブラウザ保存時にローカル時間にさらにタイムゾーンが追加される
        expires = datetime.datetime.now(datetime.timezone.utc) + expires_delta
        cookie[name]["expires"] = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")

        cookie[name]["SameSite"] = "Strict"
        cookie[name]["httponly"] = True

        if _is_secure_request():
            cookie[name]["secure"] = True

        print(cookie)
    except Exception as e:
        error(f"クッキー {name} の設定に失敗しました: {e}", "top")


def set_cookie(c_data: dict) -> None:
    _set_cookie_common("MONSTERS2", c_data, datetime.timedelta(days=60))


def set_session(data: dict = None) -> None:
    data = dict(data or {})
    data["expires_at"] = (
        datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=30)
    ).isoformat()
    _set_cookie_common("session", data, datetime.timedelta(minutes=30))


# =============#
# クッキーGET  #
# =============#
def _get_raw_cookies() -> str:
    """環境変数からクッキーデータを取得"""
    return os.environ.get("HTTP_COOKIE", "")


def _parse_cookie(raw_cookies: str, name: str) -> Dict[str, str | int]:
    """指定されたクッキーをパースして辞書を返す（無限ループ対策強化版）"""
    result: Dict[str, str | int] = {}
    if not raw_cookies:
        return result

    try:
        cook = cookies.SimpleCookie(raw_cookies)
        if name not in cook:
            return result

        # URLデコード
        encrypted_value = urllib.parse.unquote_plus(cook[name].value)

        # 復号（cryptocode → 自前関数）
        decrypted = _decrypt_cookie_value(encrypted_value, Conf["secret_key"])

        # 復号失敗チェック
        if decrypted is None or not isinstance(decrypted, str) or not decrypted.strip():
            print(f"<!-- Cookie decrypt failed for {name} -->", file=sys.stderr)
            return {}

        # 明らかに不正なデータの場合も破棄
        if decrypted.count(":") < 1:
            print(
                f"<!-- Cookie decrypt result looks corrupted for {name} -->",
                file=sys.stderr,
            )
            return {}

        # ここで初めて分割処理
        for pair in decrypted.split(","):
            pair = pair.strip()
            if ":" in pair:
                try:
                    key, value = pair.split(":", 1)
                    result[key.strip()] = value.strip()
                except Exception:
                    continue  # 1ペアが壊れていても他のペアは試す

    except Exception as e:
        print(f"<!-- Cookie parse exception for {name}: {e} -->", file=sys.stderr)
        return {}  # ここも空辞書を返す（sys.exit() は絶対にやめる）

    return result


def get_cookie() -> Dict[str, str | int]:
    cookie = _parse_cookie(_get_raw_cookies(), "MONSTERS2")
    if not cookie or "expires_at" not in cookie:
        return {}

    return cookie


def get_session() -> Dict[str, str | int]:
    session = _parse_cookie(_get_raw_cookies(), "session")

    # セッションが明らかに壊れている場合は空で返す
    if not session or "expires_at" not in session:
        return {}

    try:
        expires_at = datetime.datetime.fromisoformat(session["expires_at"])
        if expires_at < datetime.datetime.now(datetime.timezone.utc):
            return {}
    except Exception:
        return {}  # 期限切れ判定も失敗したら空で返す

    return session


# =============#
# CSRFトークン #
# =============#
def generate_csrf_token(session: dict) -> str:
    token = secrets.token_hex(16)
    session["csrf_token"] = token
    set_session(session)  # クッキーを即時保存
    return token


def verify_csrf_token(submitted_token: str, session: dict) -> bool:
    return secrets.compare_digest(submitted_token or "", session.get("csrf_token", ""))


def token_check(FORM: dict, session: dict, login_data: dict | None = None) -> dict:
    form_token = FORM.get("token", "").strip()
    session_token = session.get("token", "").strip()

    if not form_token or not secrets.compare_digest(session_token, form_token):
        # error("無効なセッションです。再度お試しください", "")
        f"無効なセッションです。再度お試しください {form_token}, セッション：{session_token} ",

    session.update(
        {
            "ref": "",
            "token": secrets.token_hex(16),
        }
    )

    # ログイン直後の確定情報を session に載せる
    if login_data:
        session.update(login_data)
    elif not session.get("in_name"):
        session["in_name"] = FORM.get("user_name", "")

    set_session(session)
    return session
