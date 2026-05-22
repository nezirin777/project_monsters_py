# validation.py - フォームの定義とバリデーション処理

import os
import unicodedata
import re
import emoji
import hmac
from typing import NoReturn
from wtforms import Form, StringField, PasswordField, IntegerField, validators
from wtforms.validators import ValidationError

from sub_def.utils import error
from sub_def.crypto import (
    verify_password,
    pass_encode,
    hash_password,
    get_cookie,
    set_cookie,
)
from sub_def.file_ops import (
    open_user_all,
    save_user_all,
)

import conf

Conf = conf.Conf

# -------------------------------------------------------
# 禁止ユーザー名リスト
#   - Windows ファイルシステムの予約語（デバイス名）
#   - ゲーム固有の予約ディレクトリ名（logs, lock_fol）
# ユーザーフォルダ名として使われるため、OS が予約している名前は
# ディレクトリ作成に失敗したり予期しない挙動を引き起こす。
# -------------------------------------------------------
_NG_STR_RAW: list[str] = [
    # ゲーム固有の予約ディレクトリ
    "logs",
    "lock_fol",
    # Windows デバイス名予約語
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "COM5",
    "COM6",
    "COM7",
    "COM8",
    "COM9",
    "LPT1",
    "LPT2",
    "LPT3",
    "LPT4",
    "LPT5",
    "LPT6",
    "LPT7",
    "LPT8",
    "LPT9",
]

# 大文字小文字を問わず O(1) で照合するため frozenset に変換する
_NG_STR_UPPER: frozenset[str] = frozenset(name.upper() for name in _NG_STR_RAW)


# ======================#
# カスタムバリデータ    #
# ======================#
class ZeroAllowedDataRequired:
    """
    0 を有効な値として扱う DataRequired 代替バリデータ。
    WTForms 標準の DataRequired は 0 を falsy と判定して弾くため独自実装している。
    """

    def __init__(self, message: str = None):
        self.message = message or "This field is required."

    def __call__(self, form: Form, field) -> None:
        if field.data is None or (
            isinstance(field.data, str) and not field.data.strip()
        ):
            raise ValidationError(self.message)
        if field.data == 0:
            return
        if not field.data:
            raise ValidationError(self.message)


class ValidUsername:
    """ユーザー名の詳細バリデーション（文字種・絵文字・Shift-JIS・予約語）"""

    def __call__(self, form: Form, field) -> None:
        # NFKC 正規化（全角英数→半角など）して field.data に書き戻す。
        # 以降の処理はすべて正規化済みの値を使う。
        user_name = unicodedata.normalize("NFKC", field.data.strip())
        field.data = user_name

        # ファイルシステムで問題になる文字・末尾スペース・ドットを禁止する
        if re.search(r'[.<>:"/\\|?*\x00-\x1F\s]|[. ]$', user_name):
            raise ValidationError(
                "ユーザー名に無効な文字（スペース、ドット、特殊文字）が含まれています"
            )

        if any(emoji.is_emoji(char) for char in user_name):
            raise ValidationError("ユーザー名に絵文字は使用できません")

        # Shift-JIS 表現可能チェック
        # replace エラーハンドラで変換不能文字を '?' に置き換え→元文字列と比較する。
        # 差異があれば Shift-JIS で扱えない文字が含まれていると判断する。
        try:
            encoded = user_name.encode("Shift-JIS", "replace")
            decoded = encoded.decode("Shift-JIS")
            if decoded != user_name:
                invalid_chars = [c for c, d in zip(user_name, decoded) if d == "?"]
                invalid_char = invalid_chars[0] if invalid_chars else "不明な文字"
                raise ValidationError(
                    f"ユーザー名にShift-JISで表現できない文字が含まれています: '{invalid_char}'"
                )
        except UnicodeEncodeError:
            raise ValidationError(
                "ユーザー名にShift-JISで表現できない文字が含まれています"
            )

        # 大文字小文字を問わず禁止名と照合する（frozenset で O(1)）
        if user_name.upper() in _NG_STR_UPPER:
            raise ValidationError(f"ユーザー名に予約語 '{user_name}' は使用できません")

        if any(ord(char) < 32 or ord(char) == 127 for char in user_name):
            raise ValidationError("ユーザー名に制御文字や特殊文字が含まれています")


# ======================#
# フォーム定義          #
# ======================#
class BaseUserForm(Form):
    """ログイン等で使用する基底フォーム（ユーザー名 + パスワード）"""

    user_name = StringField(
        "Username",
        [
            validators.DataRequired(message="ユーザー名を入力してください。"),
            validators.Length(
                min=2,
                max=20,
                message="ユーザー名は2文字以上20文字以下で入力してください。",
            ),
            ValidUsername(),
        ],
    )
    password = PasswordField(
        "Password",
        [
            validators.DataRequired(message="パスワードを入力してください。"),
            validators.Length(
                min=2,
                max=20,
                message="パスワードは2文字以上20文字以下で入力してください。",
            ),
        ],
    )


class LoginForm(BaseUserForm):
    pass


class RegisterForm(Form):
    """新規登録専用フォーム（フィールド名を new_user_name / new_password に変更）"""

    new_user_name = StringField(
        "Username",
        [
            validators.DataRequired(message="ユーザー名を入力してください。"),
            validators.Length(
                min=2,
                max=20,
                message="ユーザー名は2文字以上20文字以下で入力してください。",
            ),
            ValidUsername(),
        ],
    )
    new_password = PasswordField(
        "Password",
        [
            validators.DataRequired(message="パスワードを入力してください。"),
            validators.Length(
                min=2,
                max=20,
                message="パスワードは2文字以上20文字以下で入力してください。",
            ),
        ],
    )

    def validate_new_password(self, field) -> None:
        # WTForms は "validate_フィールド名" の命名規則でカスタム検証を呼び出す
        if self.new_user_name.data == field.data:
            raise ValidationError("名前とパスワードは違うものにして下さい")


class AdminForm(Form):
    m_name = StringField("Master Name", [validators.DataRequired()])
    m_password = PasswordField("Master Password", [validators.DataRequired()])


class PresentMonsterForm(Form):
    mons_name = StringField("monster name", [validators.DataRequired()])
    sex = StringField("monster sex", [validators.DataRequired()])
    max_level = IntegerField(
        "monster maxLv",
        [validators.DataRequired(), validators.NumberRange(10, 9999999999)],
    )
    haigou = IntegerField(
        "monster 配合回数",
        [ZeroAllowedDataRequired(), validators.NumberRange(0, 9999999999)],
    )


class PresentForm(Form):
    target_name = StringField("target_name", [validators.DataRequired()])
    money = IntegerField(
        "money", [ZeroAllowedDataRequired(), validators.NumberRange(0, 9999999999)]
    )
    medal = IntegerField(
        "medal", [ZeroAllowedDataRequired(), validators.NumberRange(0, 9999999999)]
    )
    key = IntegerField(
        "key", [ZeroAllowedDataRequired(), validators.NumberRange(0, 9999999999)]
    )


class NewPassForm(Form):
    target_name = StringField("target_name", [validators.DataRequired()])
    newpass = PasswordField(
        "New Password",
        [
            validators.DataRequired(),
            validators.Length(
                min=2,
                max=20,
                message="パスワードは2文字以上20文字以下で入力してください。",
            ),
        ],
    )


class NameChangeForm(Form):
    """ユーザー名変更専用フォーム"""

    new_name = StringField(
        "新しいユーザー名",
        [
            validators.DataRequired(message="新しい名前を入力してください。"),
            validators.Length(
                max=20, message="新しい名前は20文字以下で入力してください。"
            ),
            ValidUsername(),
        ],
    )


# ======================#
# バリデーション関数    #
# ======================#
def validate_form(form: Form, jump: str = "top") -> bool:
    """
    WTForms フォームを検証し、失敗時は error() でリダイレクトする。

    Args:
        form: 検証対象のフォームインスタンス
        jump: 検証失敗時のリダイレクト先（error() の jump 引数と同じ）
    """
    if not form.validate():
        error_msg = "; ".join(
            f"{field}: {errors[0]}" for field, errors in form.errors.items()
        )
        error(f"入力情報の検証に失敗しました: {error_msg}", jump)
    return True


def check_valid_user_name_password(FORM: dict) -> RegisterForm:
    """新規登録フォームのバリデーションを行い、正規化済みフォームを返す"""
    form = RegisterForm(data=FORM)
    validate_form(form, "top")
    return form


def admin_check(FORM: dict) -> AdminForm:
    """
    管理者名・パスワードを検証する。
    タイミング攻撃対策として hmac.compare_digest による定時間比較を使う。
    """
    form = AdminForm(data=FORM)
    validate_form(form, "kanri")

    # 非 ASCII 文字による TypeError を防ぐためバイト列で比較する
    m_name_bytes = form.m_name.data.encode("utf-8")
    conf_name_bytes = Conf["master_name"].encode("utf-8")
    m_pass_bytes = form.m_password.data.encode("utf-8")
    conf_pass_bytes = Conf["master_password"].encode("utf-8")

    if not hmac.compare_digest(m_name_bytes, conf_name_bytes):
        error("MASTER_NAMEが違います", "kanri")
    if not hmac.compare_digest(m_pass_bytes, conf_pass_bytes):
        error("MASTER_PASSWORDが違います", "kanri")

    return form


def present_monster_check(FORM: dict) -> PresentMonsterForm:
    form = PresentMonsterForm(data=FORM)
    validate_form(form, "kanri")
    return form


def present_check(FORM: dict) -> PresentForm:
    form = PresentForm(data=FORM)
    validate_form(form, "kanri")
    return form


def newpass_check(FORM: dict) -> NewPassForm:
    form = NewPassForm(data=FORM)
    validate_form(form, "kanri")
    return form


def name_change_check(FORM: dict) -> NameChangeForm:
    """
    ユーザー名変更フォームを検証して正規化済みフォームを返す。

    処理内容:
        - ValidUsername による NFKC 正規化・文字種検証
        - 新しい名前とパスワードの一致チェック
    """
    form = NameChangeForm(data=FORM)
    validate_form(form, "my_page")

    # ValidUsername により NFKC 正規化済みの値を使う
    new_name = form.new_name.data
    password = FORM.get("password", "")

    if new_name and password and new_name == password:
        error("新しい名前とパスワードは違うものにしてください。", jump="my_page")

    return form


def login_check(FORM: dict) -> dict:
    """
    ログイン認証を行い、成功時はセッション初期化用の辞書を返す。

    旧式パスワード（SHA-1 Base64）を検知した場合は SHA-256 形式へ自動マイグレートする。
    """
    wtform = LoginForm(data=FORM)
    validate_form(wtform, "top")

    name = wtform.user_name.data
    password = wtform.password.data

    user_path = os.path.join(Conf["savedir"], name)
    if not os.path.exists(user_path):
        error("あなたは未登録のようです。", "top")

    all_data = open_user_all(name)
    user = all_data.get("user", {})

    # 旧式ハッシュ（コロンなし = SHA-1 Base64）を検知して新形式へ移行する。
    # pass_encode は移行判定にのみ使用する（crypto.py 参照）。
    if ":" not in user.get("pass", ""):
        if user.get("pass") == pass_encode(password):
            user["pass"] = hash_password(password)
            all_data["user"] = user
            save_user_all(all_data, name)

    if not verify_password(password, user.get("pass", "")):
        error("パスワードが違います", "top")

    # 旧クッキーのパスワードフィールドを削除してセキュリティを向上させる
    cookie = get_cookie()
    cookie.pop("in_pass", None)
    cookie["in_name"] = name
    set_cookie(cookie)

    # my_page 表示に必要な最小限の情報を返す
    return {
        "in_name": name,
        "last_floor": user.get("last_floor", 1),
        "last_room": user.get("last_room", ""),
        "last_floor_isekai": user.get("last_floor_isekai", 0),
        "next_t": user.get("next_t", 0),
    }
