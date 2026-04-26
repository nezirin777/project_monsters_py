# kyoukai.py - 教会でのお祈り処理

from sub_def.file_ops import open_user_all, save_user_all
from sub_def.utils import error, success


def recover_monster(monster):
    """モンスターのHP・MPを回復し、回復コストを計算"""
    if monster["hp"] == 0:
        monster["hp"], monster["mp"] = monster["mhp"], monster["mmp"]
        return (monster["mhp"] + monster["mmp"]) * 2
    return 0


def kyoukai(FORM):
    """お祈りによりパーティのHP・MPを回復し、費用を更新（user_all対応）"""
    # user_all で全データを一括取得
    user_name = FORM["s"]["in_name"]
    all_data = open_user_all(user_name)
    user = all_data["user"]
    party = all_data["party"]

    # 回復処理と費用計算
    total_cost = sum(recover_monster(pt) for pt in party)

    # エラーチェック
    if total_cost == 0:
        error("現在お祈りする必要はありません")

    if user["money"] < total_cost:
        error("お金が足りません")

    # 所持金更新
    user["money"] -= int(total_cost)

    # user_all に反映して保存（partyも含めて1回で保存）
    all_data["user"] = user
    all_data["party"] = party
    save_user_all(all_data, user_name)

    success("お祈りが天にとどきました")
