# kyoukai.py - 教会でのお祈り処理


from sub_def.file_ops import open_user, save_user, open_party, save_party
from sub_def.utils import error, success


def recover_monster(monster):
    """モンスターのHP・MPを回復し、回復コストを計算"""
    if monster["hp"] == 0:
        monster["hp"], monster["mp"] = monster["mhp"], monster["mmp"]
        return (monster["mhp"] + monster["mmp"]) * 2
    return 0


def kyoukai(FORM):
    """お祈りによりパーティのHP・MPを回復し、費用を更新"""
    user = open_user()
    party = open_party()

    # 回復と費用計算
    total_cost = sum(recover_monster(pt) for pt in party)

    # エラーチェック
    if total_cost == 0:
        error("現在お祈りする必要はありません")

    if user["money"] < total_cost:
        error("お金が足りません")

    # 所持金更新と保存
    user["money"] -= int(total_cost)
    save_user(user)
    save_party(party)

    success("お祈りが天にとどきました")
