# yadoya.py - 宿屋の処理

from sub_def.file_ops import open_user_all, save_user_all
from sub_def.utils import error, success


def yadoya(FORM):
    user_name = FORM["s"]["in_name"]

    user_all = open_user_all(user_name)
    user = user_all["user"]
    party = user_all["party"]

    yadodai = sum(
        (pt["mhp"] - pt["hp"]) + (pt["mmp"] - pt["mp"]) for pt in party if pt["hp"] != 0
    )

    if yadodai <= 0:
        error("現在宿泊する必要はありません。", jump="my_page")
    if user["money"] < yadodai:
        error("お金が足りません", jump="my_page")

    for pt in party:
        if pt["hp"] != 0:
            pt["hp"] = pt["mhp"]
            pt["mp"] = pt["mmp"]

    user["money"] -= int(yadodai)

    user_all["user"] = user
    user_all["party"] = party
    save_user_all(user_all, user_name)

    success("HP・MPが全回復しました", jump="my_page")
