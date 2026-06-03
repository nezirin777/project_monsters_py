# yadoya.py - 宿屋の処理

from sub_def.file_ops import open_user_all, save_user_all
from sub_def.utils import error, success


def yadoya(FORM: dict) -> None:
    """
    宿屋への宿泊処理。HP・MP が欠けているモンスターを回復し、宿泊代を徴収する。

    宿泊代 = 全モンスターの (最大HP - 現HP) + (最大MP - 現MP) の合計。
    HP が 0（戦闘不能）のモンスターは回復対象外。
    """
    session = FORM.get("s", {})
    user_name = session.get("in_name")

    user_all = open_user_all(user_name)
    user = user_all.get("user", {})
    party = user_all.get("party", [])

    # 文字列データ（"0" など）が混ざっていても正しく計算できるよう int() で安全にキャスト
    # HP が 0（戦闘不能）のモンスターは宿泊代の計算から除外する
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

    # 生存中のモンスターのみ HP・MP を最大値まで回復する
    for pt in party:
        if int(pt.get("hp", 0)) != 0:
            pt["hp"] = int(pt.get("mhp", 1))
            pt["mp"] = int(pt.get("mmp", 0))

    # yadodai は sum() の戻り値なので int 型が保証されている
    user["money"] = int(user.get("money", 0)) - yadodai

    user_all["user"] = user
    user_all["party"] = party
    save_user_all(user_all, user_name)

    success("HP・MPが全回復しました", jump="my_page")
