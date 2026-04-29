# number_unit.py - 数値表記変換の処理


def number_unit(FORM):
    from sub_def.crypto import get_cookie, set_cookie
    from sub_def.utils import success

    cookie = get_cookie()
    cookie["unit_type"] = FORM["no"]
    set_cookie(cookie)

    success("単位表記を変更しました。", jump="my_page")
