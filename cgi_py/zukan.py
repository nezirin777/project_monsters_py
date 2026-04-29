# zukan.py - 図鑑ページ処理

from sub_def.file_ops import open_user_all, open_monster_dat
from sub_def.utils import print_html
from sub_def.crypto import get_cookie

import conf

Conf = conf.Conf


def zukan(FORM):

    user_name = FORM.get("user_name")
    m_type = FORM.get("type", "")
    fol = FORM.get("fol", "")

    user_all = open_user_all(user_name)

    user = user_all["user"]
    zukan = user_all["zukan"]

    M_list = open_monster_dat()

    ccc = get_cookie()
    ref = ccc.get("in_name", "") == user_name

    zukan_list = {name: zu for name, zu in zukan.items() if (m_type == zu["m_type"])}

    content = {
        "Conf": Conf,
        "user_name": user_name,
        "user": user,
        "zukan_list": zukan_list,
        "m_type": m_type,
        "M_list": M_list,
        "ref": ref,
        "fol": fol,
        "token": FORM["s"]["token"],
    }

    print_html("zukan_tmp.html", content)
