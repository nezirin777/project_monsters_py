# kyoukai.py - 教会での処理を担当するモジュール

from sub_def.file_ops import open_user, save_user, open_party, save_party
from sub_def.utils import print_json
import json


def recover_monster(monster):
    """モンスターのHP・MPを回復し、回復コストを計算"""
    if monster["hp"] == 0:
        monster["hp"], monster["mp"] = monster["mhp"], monster["mmp"]
        return (monster["mhp"] + monster["mmp"]) * 2
    return 0


def kyoukai_ok(FORM):
    user = open_user()
    party = open_party()

    total_cost = sum(recover_monster(pt) for pt in party)

    # エラーチェック
    if user["money"] < total_cost:
        print_json({"error": "お金が足りません"})
        return
    elif total_cost == 0:
        print_json({"error": "現在お祈りする必要はありません"})
        return

    user["money"] -= total_cost
    save_user(user)
    save_party(party)

    print_json({"success": True})
