# validation.py - フォームの定義とバリデーション処理

import os
import unicodedata
import re
import emoji
import hmac
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

# Windows予約語
NG_STR = [
    "logs",
    "lock_fol",
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


# ======================#
# カスタムバリデータ
# ======================#
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


class ValidUsername:
    """ユーザー名の詳細な検証"""

    def __call__(self, form, field):
        user_name = unicodedata.normalize("NFKC", field.data.strip())

        if re.search(r'[.<>:"/\\|?*\x00-\x1F\s]|[. ]$', user_name):
            raise ValidationError(
                "ユーザー名に無効な文字（スペース、ドット、特殊文字）が含まれています"
            )

        if any(emoji.is_emoji(char) for char in user_name):
            raise ValidationError("ユーザー名に絵文字は使用できません")

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

        if user_name.upper() in [name.upper() for name in NG_STR]:
            raise ValidationError(f"ユーザー名に予約語 '{user_name}' は使用できません")

        if any(ord(char) < 32 or ord(char) == 127 for char in user_name):
            raise ValidationError("ユーザー名に制御文字や特殊文字が含まれています")


# ======================#
# フォーム定義
# ======================#
class BaseUserForm(Form):
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


class RegisterForm(BaseUserForm):
    def validate_password(self, field):
        if self.user_name.data == field.data:
            raise ValidationError("名前とパスワードは違うものにして下さい")


class LoginForm(BaseUserForm):
    pass


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
    """ユーザー名変更専用のシンプルなフォーム"""

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
# バリデーション関数
# ======================#
def validate_form(form, error_context="top"):
    """共通のフォームバリデーション処理"""
    if not form.validate():
        error_msg = "; ".join(
            f"{field}: {errors[0]}" for field, errors in form.errors.items()
        )
        error(f"入力情報の検証に失敗しました: {error_msg}", error_context)
    return True


def check_valid_user_name_password(FORM):
    form = RegisterForm(data=FORM)
    validate_form(form, "top")
    return form


def admin_check(FORM):
    form = AdminForm(data=FORM)
    validate_form(form, "kanri")

    if not hmac.compare_digest(form.m_name.data, Conf["master_name"]):
        error("MASTER_NAMEが違います", "kanri")
    if not hmac.compare_digest(form.m_password.data, Conf["master_password"]):
        error("MASTER_PASSWORDが違います", "kanri")

    return form


def present_monster_check(FORM):
    form = PresentMonsterForm(data=FORM)
    validate_form(form, "kanri")
    return form


def present_check(FORM):
    form = PresentForm(data=FORM)
    validate_form(form, "kanri")
    return form


def newpass_check(FORM):
    form = NewPassForm(data=FORM)
    validate_form(form, "kanri")
    return form


def login_check(FORM):
    """ログイン処理（user_all対応版）"""
    wtform = LoginForm(data=FORM)
    validate_form(wtform, "top")

    name = wtform.user_name.data
    password = wtform.password.data

    user_path = os.path.join(Conf["savedir"], name)
    if not os.path.exists(user_path):
        error("あなたは未登録のようです。", "top")

    # 新形式：open_user_all を使用
    all_data = open_user_all(name)
    user = all_data.get("user", {})

    # 旧式パスワード → 新方式へ移行
    if ":" not in user.get("pass", ""):
        if user.get("pass") == pass_encode(password):
            user["pass"] = hash_password(password)
            all_data["user"] = user
            save_user_all(all_data, name)

    if not verify_password(password, user.get("pass", "")):
        error("パスワードが違います", "top")

    # Cookieはユーザー名だけ保持
    cookie = get_cookie()
    cookie.pop("in_pass", None)
    cookie["in_name"] = name
    set_cookie(cookie)

    # my_page表示に必要な最小限の情報を返す
    return {
        "in_name": name,
        "last_floor": user.get("last_floor", 1),
        "last_room": user.get("last_room", ""),
        "last_floor_isekai": user.get("last_floor_isekai", 0),
        "next_t": user.get("next_t", 0),
    }
