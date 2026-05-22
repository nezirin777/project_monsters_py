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

# CGI は1リクエスト1プロセスで動作するため、このキャッシュはリクエスト内の
# 二重読み込みを防ぐためだけに存在する（プロセス間共有は行われない）
_cookie_cache: dict | None = None
_session_cache: dict | None = None

# AES-GCM の構造: nonce(16) + ciphertext(可変) + tag(16)
_GCM_NONCE_SIZE = 16
_GCM_TAG_SIZE = 16
_GCM_MIN_SIZE = _GCM_NONCE_SIZE + _GCM_TAG_SIZE  # コンテンツなしの最小サイズ


# ------------------- ヘルパー関数 -------------------
def _encrypt_cookie_value(data: str, secret_key: str) -> str:
    """クッキー値を AES-GCM で暗号化して Base64 URL-safe 文字列を返す"""
    key = hashlib.sha256(secret_key.encode("utf-8")).digest()
    cipher = AES.new(key, AES.MODE_GCM)
    ciphertext, tag = cipher.encrypt_and_digest(data.encode("utf-8"))
    encrypted = cipher.nonce + ciphertext + tag
    return base64.urlsafe_b64encode(encrypted).decode("utf-8")


def _decrypt_cookie_value(encrypted_b64: str, secret_key: str) -> str:
    """Base64 URL-safe 文字列を AES-GCM で復号して元の文字列を返す"""
    key = hashlib.sha256(secret_key.encode("utf-8")).digest()
    data = base64.urlsafe_b64decode(encrypted_b64)

    # データが最低限の長さを満たしているかチェック（不正クッキー対策）
    if len(data) < _GCM_MIN_SIZE:
        raise ValueError(f"暗号化データが短すぎます: {len(data)} bytes")

    nonce = data[:_GCM_NONCE_SIZE]
    ciphertext = data[_GCM_NONCE_SIZE:-_GCM_TAG_SIZE]
    tag = data[-_GCM_TAG_SIZE:]
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    plaintext = cipher.decrypt_and_verify(ciphertext, tag)
    return plaintext.decode("utf-8")


# ===========#
# 暗号化     #
# ===========#
def pass_encode(p: str) -> str:
    """
    【旧式パスワードハッシュ】移行処理専用。新規利用禁止。
    login_check() でのマイグレーション判定にのみ使用する。
    新規パスワードは hash_password() を使うこと。
    """
    return base64.b64encode(hashlib.sha1(str(p).encode("utf-8")).digest()).decode()


def hash_password(password: str) -> str:
    """パスワードをランダムソルト付き SHA-256 でハッシュ化する。保存形式: 'salt_hex:hash_hex'"""
    try:
        salt = os.urandom(8)
        hashed = hashlib.sha256(salt + password.encode("utf-8")).hexdigest()
        return f"{salt.hex()}:{hashed}"
    except Exception as e:
        logging.error(f"パスワードハッシュ化エラー: {e}")
        raise RuntimeError("パスワードの処理に失敗しました。")


def verify_password(password: str, stored_hash: str) -> bool:
    """入力パスワードが保存済みハッシュと一致するか検証する"""
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
    """現在のリクエストが HTTPS かどうかを判定する"""
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
    """
    指定した辞書データを暗号化してクッキーとして出力する。

    データのエンコード形式: "key:value,key:value,..."
    値にカンマやコロンを含む場合も split(":", 1) と split(",") の組み合わせで
    正しく分離できるが、キー名にはコロン・カンマを使わないこと。
    """
    try:
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
        logging.error(f"クッキー {name} の設定に失敗しました: {e}")
        raise RuntimeError("クッキーの設定に失敗しました。")


def set_cookie(c_data: dict) -> None:
    """ユーザー識別情報を永続クッキー（60日）として保存する"""
    global _cookie_cache
    c_data = dict(c_data)
    c_data["expires_at"] = (
        datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=46)
    ).isoformat()
    _cookie_cache = c_data
    _set_cookie_common("MONSTERS2", c_data, datetime.timedelta(days=60))


def set_session(data: dict = None) -> None:
    """セッション情報をセッションクッキー（30分）として保存する"""
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
    """指定名のクッキーを復号して辞書に変換する。失敗時は空辞書を返す"""
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
                    # split(":", 1) で値側のコロン（ISO日時など）を保護する
                    key, value = pair.split(":", 1)
                    result[key.strip()] = value.strip()
                except Exception:
                    continue

    except Exception as e:
        logging.warning(f"Cookie parse exception for {name}: {e}")
        return {}

    return result


def _is_expired(data: dict) -> bool:
    """data 内の expires_at が現在時刻を過ぎているか判定する"""
    if "expires_at" not in data:
        return True
    try:
        expires_at = datetime.datetime.fromisoformat(data["expires_at"])
        return expires_at < datetime.datetime.now(datetime.timezone.utc)
    except Exception:
        return True


def get_cookie() -> Dict[str, str]:
    """ユーザー識別クッキーを取得する。期限切れ・不正な場合は空辞書を返す"""
    global _cookie_cache
    if _cookie_cache is not None:
        return _cookie_cache

    cookie = _parse_cookie(_get_raw_cookies(), "MONSTERS2")

    if not cookie or _is_expired(cookie):
        _cookie_cache = {}
        return _cookie_cache

    _cookie_cache = cookie
    return cookie


def get_session() -> Dict[str, str]:
    """セッションクッキーを取得する。期限切れ・不正な場合は空辞書を返す"""
    global _session_cache
    if _session_cache is not None:
        return _session_cache

    session = _parse_cookie(_get_raw_cookies(), "session")

    if not session or _is_expired(session):
        _session_cache = {}
        return _session_cache

    _session_cache = session
    return session


# =============#
# CSRFトークン #
# =============#
def generate_csrf_token(session: dict) -> str:
    """新しい CSRF トークンを生成してセッションに保存し、トークン文字列を返す"""
    token = secrets.token_hex(16)
    session["csrf_token"] = token
    set_session(session)
    return token


def verify_csrf_token(submitted_token: str, session: dict) -> bool:
    """フォームから送られたトークンとセッションのトークンをタイミング安全比較する"""
    return secrets.compare_digest(submitted_token or "", session.get("csrf_token", ""))


def token_check(FORM: dict, session: dict, login_data: dict = None) -> dict:
    """
    CSRF トークンを検証してセッションを更新する。
    検証失敗時は error() を呼んでリダイレクトする。

    Note: utils.error の循環インポートを避けるため、関数内でインポートしている。
          crypto → utils の依存を避けるための意図的な構造。
    """
    form_token = FORM.get("token", "").strip()
    session_token = session.get("token", "").strip()

    if not form_token or not secrets.compare_digest(session_token, form_token):
        from .utils import error

        error("無効なセッションです。再度お試しください", "")

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
