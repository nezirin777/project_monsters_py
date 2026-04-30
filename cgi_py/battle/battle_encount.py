# battle_encount.py - 戦闘出現モンスター決定処理

import random
from sub_def.file_ops import (
    open_user_all,
    open_monster_dat,
    open_monster_boss_dat,
    save_battle,
)
from sub_def.monster_ops import battle_mob_select, battle_boss_select
from sub_def.utils import slim_number_with_cookie, env, error

import conf

Conf = conf.Conf


def calculate_floor_and_hosei(floor, special_monster=None, user_key=0):
    """階層と補正値を計算"""
    kaisou = floor
    while kaisou > 500:
        kaisou -= 500
    base_hosei = floor * (floor / 500 if floor > 500 else 1)

    # 特殊モンスターによる補正計算を定義
    special_hosei_calculators = {
        "わたぼう": lambda f, _: (f + 30) * ((f / 500) * 1.3 if f > 500 else 1),
        "スライム": lambda f, _: (f + 30) * ((f / 500) * 1.3 if f > 500 else 1),
        "vipsg": lambda f, k: (f + 100) * (k / 2000),
        "異世界": lambda f, k: (f + k) * ((f + k) / 500),
    }

    # 通常の補正値を適用するか、特殊モンスターの計算式を適用
    hosei = special_hosei_calculators.get(special_monster, lambda f, k: base_hosei)(
        floor, user_key
    )

    return kaisou, hosei


def get_monster_list(floor, room_type, party, special_monster=None):
    """モンスターリストのフィルタリング"""
    monsters = (
        open_monster_boss_dat() if special_monster == "vipsg" else open_monster_dat()
    )

    if special_monster == "vipsg":
        return [
            name for name, mon in monsters.items() if mon.get("type") == "VIPSガールズ"
        ]

    aite = [
        name
        for name, mon in monsters.items()
        if mon.get("階層A", 0) <= floor <= mon.get("階層B", 0)
        and (
            room_type == "通常"
            and mon.get("room") not in ("異世界", "？？？系")
            or room_type == mon.get("room")
        )
    ]

    if special_monster == "異世界":
        # きゅうべぇ出現判定
        if 21 <= floor <= 30:
            for member in party[: min(len(party), 3)]:
                member_mon = monsters.get(member.get("name"))
                if member_mon and member_mon.get("room") == "異世界":
                    aite.append("キュゥべえ")

    if not aite:
        error("対戦相手モンスターを選択できませんでした。", jump="my_page")

    return aite


def prepare_teki_list(monster_names, hosei, floor, special_monster=None, user_key=0):
    """敵リストを作成し、重複名を調整"""
    teki = [{"name": "", "exp": 0, "money": 0, "down": 1}]  # 0番目はダミー

    if special_monster in ("わたぼう", "スライム"):
        teki.append(battle_mob_select(special_monster, hosei, floor))
        return teki

    if special_monster == "vipsg":
        selected_monsters = random.sample(monster_names, k=min(3, len(monster_names)))
        teki += [
            battle_boss_select(name, hosei, user_key) for name in selected_monsters
        ]
        return teki

    if special_monster == "異世界":
        selected_monsters = random.sample(monster_names, k=min(3, len(monster_names)))
        teki.extend(
            battle_mob_select(name, hosei, floor + user_key)
            for name in selected_monsters
        )
        return teki

    teki_kazu = random.choices([1, 2, 3], k=1, weights=[3, 2, 1])[0]
    selected_monsters = random.choices(monster_names, k=teki_kazu)
    teki.extend([battle_mob_select(name, hosei, floor) for name in selected_monsters])

    # 敵の名前重複を回避
    name_counts = {}
    for entry in teki[1:]:  # ダミーの0番目をスキップ
        name = entry.get("name")
        if not name:
            continue

        if name in name_counts:
            name_counts[name] += 1
            # _A, _B などを付与（"name2"キーが存在する前提）
            if "name2" in entry:
                entry["name2"] += f"_{chr(64 + name_counts[name])}"
        else:
            name_counts[name] = 1

    return teki


def render_battle(teki, target):
    """バトルデータをレンダリングしてHTMLを生成（文字列として返す）"""
    template = env.get_template("battle_encount_tmp.html")
    teki_v = slim_number_with_cookie(teki)
    return template.render(Conf=Conf, tekis=teki_v[1:], target=target)


def battle_encount(FORM, special_monster=None):
    """バトルエンカウントの生成（通常・異世界）"""
    session = FORM.get("s", {})
    user_name = session.get("in_name")

    if not user_name:
        error("ユーザー名が取得できませんでした。", "top")

    # 通常と異世界の入力を判断して階層を取得
    in_floor = int(FORM.get("in_floor") or FORM.get("in_isekai", 1))
    in_room = FORM.get("in_room", "通常")

    # 新方式：user_allで一括取得
    all_data = open_user_all(user_name)
    user = all_data.get("user", {})
    party = all_data.get("party", [])

    user_key = user.get("key", 0) if special_monster in ("vipsg", "異世界") else 0
    pt_num = (
        min(len(party), 3) if special_monster not in ("わたぼう", "スライム") else 1
    )

    # 階層と補正値の計算
    kaisou, hosei = calculate_floor_and_hosei(in_floor, special_monster, user_key)

    # モンスターリスト取得
    monster_names = get_monster_list(
        kaisou, in_room, party, special_monster=special_monster
    )

    # 敵リストを作成
    teki = prepare_teki_list(monster_names, hosei, in_floor, special_monster, user_key)

    # ユーザー名指定のsave_battleで保存
    save_battle({"party": party[:pt_num], "teki": teki}, user_name)

    teki_v = slim_number_with_cookie(teki)
    return {"target": special_monster, "tekis": teki_v[1:]}
