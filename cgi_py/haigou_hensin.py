# haigou_hensin.py - 配合による新モンスター生成と表示

from sub_def.utils import print_html, error
from sub_def.file_ops import open_user_all, save_user_all, open_monster_dat
from sub_def.monster_ops import monster_select, register_monster_progress

import conf

Conf = conf.Conf


def haigou_hensin(FORM):
    """配合による新モンスター生成と表示"""
    # セッションからの引き継ぎデータ取得
    new_m = FORM["s"].get("new_mons", "").replace("フィッシュル(制服)", "フィッシュル")
    user_name = FORM["s"].get("in_name")

    try:
        # haigou_check.py で保存された配列インデックス(0始まり)をそのまま使用
        haigou1 = int(FORM["s"].get("haigou1", -1))
        haigou2 = int(FORM["s"].get("haigou2", -1))
    except ValueError:
        error("配合データが不正です。最初からやり直してください。", jump="my_page")

    # セッションの真偽値は文字列化されている場合とそのままの場合があるため安全に判定
    hint_flag_val = FORM["s"].get("hint_flag")
    hint_flag = hint_flag_val in (True, "True", "true", 1, "1")

    # user_all で全データを一括取得
    all_data = open_user_all(user_name)
    user = all_data.get("user", {})
    party = all_data.get("party", [])

    # セッション切れ等による不正アクセス防止
    if haigou1 < 0 or haigou2 < 0 or haigou1 >= len(party) or haigou2 >= len(party):
        error(
            "配合データが見つかりません。最初からやり直してください。", jump="my_page"
        )

    hai_A = party[haigou1]
    hai_B = party[haigou2]

    cost = (hai_A.get("lv", 1) + hai_B.get("lv", 1)) * 10

    # お金消費
    if user.get("money", 0) < cost:
        error("お金が足りません", jump="my_page")
    user["money"] -= cost

    # 新モンスターのパラメータ計算
    mlv = int(hai_A.get("lv", 1) + hai_B.get("lv", 1))
    new_hai = hai_A.get("hai", 0) + hai_B.get("hai", 0) + 1
    hosei = max(new_hai // 2, 1)

    # 新モンスターデータの生成
    new_mob = monster_select(new_m, hosei)

    # 技の判定が必要になったら、その場でマスターデータを引く
    Mons = open_monster_dat()
    new_mob_name = new_mob["name"]
    mon_master = Mons.get(new_mob_name, {})
    waza_target = mon_master.get("waza", "")

    # 特技・図鑑登録を統合関数で処理
    progress = register_monster_progress(
        waza_target=waza_target,
        zukan_target=new_mob_name,
        user_name=user_name,
    )

    is_waza = progress["waza_new"]
    is_new = progress["zukan_new"]

    is_rare = Mons.get(mon_master["room"], {}) == "異世界"

    # 配合後モンスターに引き継ぐステータスを上書き
    new_mob.update(
        {
            "name": FORM["s"].get("new_mons", new_mob_name),
            "hai": new_hai,
            "lv": 1,
            "mlv": mlv,
        }
    )

    # 親モンスターの削除（番号が後ろの方から消さないとインデックスがずれる）
    for idx in sorted([haigou1, haigou2], reverse=True):
        del party[idx]

    # 子供モンスターをパーティの末尾に追加
    party.append(new_mob)

    # モンスターのインデックス(no)を更新して整合性を保つ
    for i, pt in enumerate(party, 1):
        pt["no"] = i

    # 保存（すべて user_all にまとめて1回だけ）
    all_data["user"] = user
    all_data["party"] = party
    save_user_all(all_data, user_name)

    content = {
        "Conf": Conf,
        "my_data": new_mob,
        "token": FORM["s"]["token"],
        "mode": "haigou",
        "is_waza": is_waza,
        "is_new": is_new,
        "is_rare": is_rare,
        "hint_flag": hint_flag,
    }

    print_html("new_monster_tmp.html", content)
