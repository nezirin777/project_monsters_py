from sub_def.utils import print_html
from sub_def.file_ops import (
    open_user_all,
    save_user_all,
)
from sub_def.monster_ops import monster_select, register_monster_progress

import conf

Conf = conf.Conf


def haigou_hensin(FORM):
    """配合による新モンスター生成と表示"""
    new_m = FORM["s"]["new_mons"].replace("フィッシュル(制服)", "フィッシュル")

    # 配列位置に合わせ-1されたものを引き継いでいるのでそのままで大丈夫
    haigou1, haigou2 = int(FORM["s"]["haigou1"]), int(FORM["s"]["haigou2"])
    hint_flag = True if FORM["s"]["hint_flag"] == "True" else False

    # user_all で全データを一括取得
    all_data = open_user_all()
    user = all_data["user"]
    party = all_data["party"]

    hai_A = party[haigou1]
    hai_B = party[haigou2]

    cost = (hai_A["lv"] + hai_B["lv"]) * 10

    # お金消費
    user["money"] -= cost

    # 新モンスター生成
    mlv = int(hai_A["lv"] + hai_B["lv"])
    new_hai = hai_A["hai"] + hai_B["hai"] + 1
    hosei = max(new_hai // 2, 1)

    new_mob = monster_select(new_m, hosei)

    # 特技・図鑑登録を統合関数で処理
    progress = register_monster_progress(
        waza_target=new_mob.pop("waza", None),
        zukan_target=new_mob["name"],
    )
    is_waza = progress["waza_new"]
    is_new = progress["zukan_new"]

    is_rare = new_mob.get("room") == "異世界"
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

    # 保存（すべて user_all にまとめて1回だけ）
    all_data["user"] = user
    all_data["party"] = party
    save_user_all(all_data)

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
