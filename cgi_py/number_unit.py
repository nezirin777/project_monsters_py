# number_unit.py - 数値表記変換の処理

from typing import NoReturn

from sub_def.crypto import get_cookie, set_cookie
from sub_def.utils import success


def number_unit(FORM: dict) -> NoReturn:
    """クッキーの unit_type を更新して数値表記方式を切り替える"""
    cookie = get_cookie()
    cookie["unit_type"] = FORM.get("no", "0")
    set_cookie(cookie)

    success("単位表記を変更しました。", jump="my_page")
