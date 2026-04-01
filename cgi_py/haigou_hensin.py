from sub_def.utils import print_html
from sub_def.file_ops import (
    open_user,
    open_party,
    save_party,
    save_user,
)
from sub_def.monster_ops import monster_select, waza_get, zukan_get
import conf

Conf = conf.Conf


def haigou_hensin(FORM):
    """配合による新モンスター生成と表示"""
    new_m = FORM["s"]["new_mons"].replace("フィッシュル(制服)", "フィッシュル")
    # 配列位置に合わせ-1されたものを引き継いでいるのでそのままで大丈夫
    haigou1, haigou2 = int(FORM["s"]["haigou1"]), int(FORM["s"]["haigou2"])
    hint_flag = True if FORM["s"]["hint_flag"] == "True" else False

    user = open_user()
    party = open_party()

    hai_A = party[haigou1]
    hai_B = party[haigou2]

    cost = (hai_A["lv"] + hai_B["lv"]) * 10

    # ユーザーのお金を更新
    user["money"] -= cost
    save_user(user)

    # 新モンスター生成
    mlv = int(hai_A["lv"] + hai_B["lv"])
    new_hai = hai_A["hai"] + hai_B["hai"] + 1
    hosei = max(new_hai // 2, 1)

    new_mob = monster_select(new_m, hosei)

    is_waza = waza_get(new_mob.pop("waza"))
    is_new = zukan_get(new_mob["name"])
    is_rare = True if new_mob["room"] == "特殊" else False
    new_mob.pop("room")

    new_mob.update(
        {
            "name": FORM["s"]["new_mons"],
            "hai": new_hai,
            "lv": 1,
            "mlv": mlv,
        }
    )

    # 番号が後ろの方から消さないとずれる
    for idx in sorted([haigou1, haigou2], reverse=True):
        del party[idx]

    party.append(new_mob)

    # モンスターのインデックス更新
    for i, pt in enumerate(party, 1):
        pt["no"] = i

    save_party(party)

    content = {
        "Conf": Conf,
        "my_data": new_mob,
        "token": FORM["token"],
        "mode": "haigou",
        "is_waza": is_waza,
        "is_new": is_new,
        "is_rare": is_rare,
        "hint_flag": hint_flag,
    }

    print_html("new_monster_tmp.html", content)
