# sub_def/validation.py

import unicodedata
import re
import emoji
from wtforms import Form, StringField, PasswordField, IntegerField, validators
from wtforms.validators import ValidationError
import hmac

from sub_def.utils import error
import conf

Conf = conf.Conf

# Windows予約語（既存のNG_STRを前提）
NG_STR = [
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


# 既存のカスタムバリデータ
class ZeroAllowedDataRequired:
    def __init__(self, message=None):
        self.message = message or "This field is required."

    def __call__(self, form, field):
        if field.data is None or (
            isinstance(field.data, str) and not field.data.strip()
        ):
            raise ValidationError(self.message)
        if field.data == 0:
            return
        if not field.data:
            raise ValidationError(self.message)


# 新しいカスタムバリデータ
class UsernamePasswordDifferent:
    """ユーザー名とパスワードが異なることを検証"""

    def __call__(self, form, field):
        if form.new_username.data == field.data:
            raise ValidationError("名前とパスワードは違うものにして下さい")


class ValidUsername:
    """ユーザー名の詳細な検証"""

    def __call__(self, form, field):
        username = unicodedata.normalize("NFKC", field.data.strip())

        # 統合された禁止文字・条件チェック
        if re.search(r'[.<>:"/\\|?*\x00-\x1F\s]|[. ]$', username):
            raise ValidationError(
                "ユーザー名に無効な文字（スペース、ドット、特殊文字）が含まれています"
            )

        # 絵文字チェック
        if any(emoji.is_emoji(char) for char in username):
            raise ValidationError("ユーザー名に絵文字は使用できません")

        # Shift-JISエンコーディングチェック
        try:
            encoded = username.encode("Shift-JIS", "replace")
            decoded = encoded.decode("Shift-JIS")
            if decoded != username:
                invalid_chars = [c for c, d in zip(username, decoded) if d == "?"]
                invalid_char = invalid_chars[0] if invalid_chars else "不明な文字"
                raise ValidationError(
                    f"ユーザー名にShift-JISで表現できない文字が含まれています: '{invalid_char}'"
                )
        except UnicodeEncodeError:
            raise ValidationError(
                "ユーザー名にShift-JISで表現できない文字が含まれています"
            )

        # Windows予約語チェック
        if username.upper() in (name.upper() for name in NG_STR):
            raise ValidationError(f"ユーザー名に予約語 '{username}' は使用できません")

        if any(ord(char) < 32 or ord(char) == 127 for char in username):
            raise ValidationError("ユーザー名に制御文字や特殊文字が含まれています")


class register_From(Form):
    """ユーザー名とパスワードのフォーム"""

    new_username = StringField(
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
            UsernamePasswordDifferent(),
        ],
    )


class AdminForm(Form):
    """管理者認証フォーム"""

    m_name = StringField("Master Name", [validators.DataRequired()])
    m_password = PasswordField("Master Password", [validators.DataRequired()])


class present_monster_Form(Form):
    """モンスタープレゼントフォーム"""

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


class present_Form(Form):
    """プレゼントフォーム"""

    target_name = StringField("target_name", [validators.DataRequired()])
    money = IntegerField(
        "money",
        [ZeroAllowedDataRequired(), validators.NumberRange(0, 9999999999)],
    )
    medal = IntegerField(
        "medal",
        [ZeroAllowedDataRequired(), validators.NumberRange(0, 9999999999)],
    )
    key = IntegerField(
        "key",
        [ZeroAllowedDataRequired(), validators.NumberRange(0, 9999999999)],
    )


class newpass_form(Form):
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


def validate_form(form, error_context="top"):
    """共通のフォームバリデーション処理"""
    if not form.validate():
        error_msg = "; ".join(
            f"{field}: {errors[0]}" for field, errors in form.errors.items()
        )
        error(f"入力情報の検証に失敗しました: {error_msg}", error_context)
    return True


def check_valid_username_password(FORM):
    form = register_From(data=FORM)
    validate_form(form, "top")

    return


def admin_check(FORM):
    form = AdminForm(data=FORM)

    validate_form(form, "kanri")

    if not hmac.compare_digest(form.m_name.data, Conf["master_name"]):
        error("MASTER_NAMEが違います", "kanri")
    if not hmac.compare_digest(form.m_password.data, Conf["master_password"]):
        error("MASTER_PASSWORDが違います", "kanri")

    return


def present_monster_check(FORM):
    form = present_monster_Form(data=FORM)
    validate_form(form, "kanri")

    return


def present_check(FORM):
    form = present_Form(data=FORM)
    validate_form(form, "kanri")

    return


def newpass_check(FORM):
    form = newpass_form(data=FORM)
    validate_form(form, "kanri")

    return
