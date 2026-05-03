# yadoya.py - 宿屋の処理

from sub_def.file_ops import open_user_all, save_user_all
from sub_def.utils import error, success


def yadoya(FORM):
    # セッション切れ等による KeyError を防ぐための安全な取得
    session = FORM.get("s", {})
    user_name = session.get("in_name")

    if not user_name:
        error("セッション情報が不正です。", jump="top")

    user_all = open_user_all(user_name)
    user = user_all.get("user", {})
    party = user_all.get("party", [])

    # 文字列データ（"0"など）が混ざっていても正しく計算できるようにint()で安全にキャスト
    yadodai = sum(
        (int(pt.get("mhp", 1)) - int(pt.get("hp", 0)))
        + (int(pt.get("mmp", 0)) - int(pt.get("mp", 0)))
        for pt in party
        if int(pt.get("hp", 0)) != 0
    )

    if yadodai <= 0:
        error("現在宿泊する必要はありません。", jump="my_page")

    if int(user.get("money", 0)) < yadodai:
        error("お金が足りません", jump="my_page")

    # 回復処理も安全にキャストして判定・代入
    for pt in party:
        if int(pt.get("hp", 0)) != 0:
            pt["hp"] = int(pt.get("mhp", 1))
            pt["mp"] = int(pt.get("mmp", 0))

    user["money"] = int(user.get("money", 0)) - int(yadodai)

    user_all["user"] = user
    user_all["party"] = party
    save_user_all(user_all, user_name)

    success("HP・MPが全回復しました", jump="my_page")
