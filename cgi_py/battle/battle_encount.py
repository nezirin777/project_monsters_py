import random
import sub_def
import conf
from jinja2 import Environment, FileSystemLoader

Conf = conf.Conf


def calculate_floor_and_hosei(floor, special_monster=None, user_key=None):
    """階層と補正値を計算"""
    kaisou = floor
    while kaisou > 500:
        kaisou -= 500
    base_hosei = floor * (floor / 500 if floor > 500 else 1)

    # 特殊モンスターによる補正計算を定義
    special_hosei_calculators = {
        "わたぼう": lambda floor, _: (floor + 30)
        * ((floor / 500) * 1.3 if floor > 500 else 1),
        "スライム": lambda floor, _: (floor + 30)
        * ((floor / 500) * 1.3 if floor > 500 else 1),
        "vipsg": lambda _, key: (floor + 100) * (key / 2000),
        "異世界": lambda floor, key: (floor + key) * ((floor + key) / 500),
    }

    # 通常の補正値を適用するか、特殊モンスターの計算式を適用
    hosei = special_hosei_calculators.get(special_monster, lambda f, k: base_hosei)(
        floor, user_key
    )

    return kaisou, hosei


def get_monster_list(floor, room_type, special_monster=None):
    """モンスターリストのフィルタリング"""
    monsters = (
        sub_def.open_monster_boss_dat()
        if special_monster == "vipsg"
        else sub_def.open_monster_dat()
    )

    if special_monster == "vipsg":
        return [name for name, mon in monsters.items() if mon["type"] == "VIPSガールズ"]

    aite = [
        name
        for name, mon in monsters.items()
        if mon["階層A"] <= floor <= mon["階層B"]
        and (
            room_type == "通常"
            and mon["room"] not in ("特殊", "？？？系")
            or room_type == mon["room"]
        )
    ]

    if special_monster == "異世界":
        # きゅうべぇ出現判定
        party = sub_def.open_party()
        if 21 <= floor <= 30:
            for member in party[: min(len(party), 3)]:
                if monsters[member["name"]]["room"] == "特殊":
                    aite.append("キュゥべえ")

    if not aite:
        sub_def.error("対戦相手モンスターを選択できませんでした。")

    return aite


def prepare_teki_list(monsters, hosei, floor, special_monster=None, user_key=None):
    """敵リストを作成し、重複名を調整"""
    teki = [{"name": "", "exp": 0, "money": 0, "down": 1}]

    if special_monster in ("わたぼう", "スライム"):
        teki.append(sub_def.battle_mob_select(special_monster, hosei, floor))
        return teki

    if special_monster == "vipsg":
        selected_monsters = random.sample(monsters, k=3)
        teki += [
            sub_def.battle_boss_select(name, hosei, user_key)
            for name in selected_monsters
        ]
        return teki

    if special_monster == "異世界":
        monsters = random.sample(monsters, min(len(monsters), 3))
        teki.extend(
            sub_def.battle_mob_select(name, hosei, floor + user_key)
            for name in monsters
        )
        return teki

    teki_kazu = random.choices([1, 2, 3], k=1, weights=[3, 2, 1])[0]
    selected_monsters = random.choices(monsters, k=teki_kazu)
    teki.extend(
        [sub_def.battle_mob_select(name, hosei, floor) for name in selected_monsters]
    )

    # 敵の名前重複を回避
    name_counts = {}
    for entry in teki:
        name = entry["name"]
        if name in name_counts:
            name_counts[name] += 1
            entry["name2"] += f"_{chr(64 + name_counts[name])}"  # "_A", "_B"など
        else:
            name_counts[name] = 1

    return teki


def render_battle(teki, target):
    """バトルデータをレンダリングしてHTMLを生成"""
    env = Environment(loader=FileSystemLoader("./templates"))
    template = env.get_template("battle_encount_tmp.html")
    teki_v = sub_def.slim_number_with_cookie(teki)
    return template.render(
        imgpath=Conf["imgpath"], tekis=teki_v[1:], target=target, Conf=Conf
    )


def battle_encount(FORM, special_monster=None):
    """バトルエンカウントの生成（通常・異世界）"""

    # 通常と異世界の入力を判断して階層を取得
    in_floor = int(FORM.get("in_floor") or FORM.get("in_isekai"))
    in_room = FORM["in_room"]

    user_key = (
        sub_def.open_user()["key"] if special_monster in ("vipsg", "異世界") else None
    )
    party = sub_def.open_party()
    pt_num = (
        min(len(party), 3) if not special_monster in ("わたぼう", "スライム") else 1
    )

    # 階層と補正値の計算
    kaisou, hosei = calculate_floor_and_hosei(in_floor, special_monster, user_key)

    # モンスターリスト取得
    monsters = get_monster_list(kaisou, in_room, special_monster=special_monster)

    # 敵リストを作成
    teki = prepare_teki_list(monsters, hosei, in_floor, special_monster, user_key)
    sub_def.save_battle({"party": party[:pt_num], "teki": teki})

    return render_battle(teki, special_monster)
