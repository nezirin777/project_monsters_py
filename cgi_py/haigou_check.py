from jinja2 import Environment, FileSystemLoader

import sub_def
import conf

Conf = conf.Conf


def haigou_sub(base, aite, flg=0):
    # 特殊名の変換
    base, aite = [
        name if name != "フィッシュル(制服)" else "フィッシュル"
        for name in (base, aite)
    ]

    M_list = sub_def.open_monster_dat()
    base_type = M_list[base]["m_type"]
    aite_type = M_list[aite]["m_type"]

    # 新モンスター候補の初期化
    newmons = {"type_type": "", "type_indiv": "", "indiv_indiv": "", "omiai": ""}

    # 条件を満たす新モンスターを検索
    for name, mon in M_list.items():
        for n in range(1, 4):
            bloodline = mon[f"血統{n}"]
            partner = mon[f"相手{n}"]

            # 系統×系統の条件
            if base_type == bloodline and aite_type == partner:
                newmons["type_type"] = name

            # 系統×個体 or 個体×系統の条件
            if (base_type == bloodline and aite == partner) or (
                base == bloodline and aite_type == partner
            ):
                newmons["type_indiv"] = name

            # 個体×個体の条件
            if base == bloodline and aite == partner:
                newmons["indiv_indiv"] = name

            # お見合い用条件
            if (
                flg
                and base == mon.get(f"お見合いA{n}")
                and aite == mon.get(f"お見合いB{n}")
            ):
                newmons["omiai"] = name

    # 候補の優先順位に基づいて結果を決定
    for key in ["omiai", "indiv_indiv", "type_indiv", "type_type"]:
        if newmons[key]:
            return newmons[key]

    # 候補が見つからない場合は元のモンスターを返す
    return base


def haigou_check(FORM):
    # 配列位置に合わせるため-1
    haigou1 = int(FORM["haigou1"]) - 1
    haigou2 = int(FORM["haigou2"]) - 1

    token = FORM["token"]

    if haigou1 < 0 or haigou2 < 0:
        sub_def.error("正しく設定されていません-1")
    if haigou1 == haigou2:
        sub_def.error("正しく設定されていません-2")

    user = sub_def.open_user()
    party = sub_def.open_party()
    zukan = sub_def.open_zukan()

    hai_A = party[haigou1]
    hai_B = party[haigou2]

    if hai_A["sex"] == hai_B["sex"]:
        sub_def.error("陰陽が同じで配合出来ません")

    if any(hai["lv"] < Conf["haigoulevel"] for hai in (hai_A, hai_B)):
        sub_def.error(
            f"<img src={Conf['imgpath']}/{hai_A['name']}.gif>または<img src={Conf['imgpath']}/{hai_B['name']}.gif>のレベルが{Conf['haigoulevel']}に達していません"
        )

    if user["money"] < (hai_A["lv"] + hai_B["lv"]) * 10:
        sub_def.error("お金が足りません")

    new_mons = haigou_sub(hai_A["name"], hai_B["name"])
    new_mons_name = next(
        (name for name, zu in zukan.items() if new_mons == name and zu["get"]), "？？？"
    )

    # HTML出力
    # テンプレートの取得とレンダリング
    env = Environment(
        loader=FileSystemLoader("templates"), cache_size=100
    )  # テンプレートディレクトリ
    template = env.get_template("haigou_check_tmp.html")
    html = template.render(
        Conf=Conf,
        nameA=hai_A["name"],
        nameB=hai_B["name"],
        my_new_mons=new_mons_name,
        target="",
        token=token,
        mode="haigou",
    )

    sub_def.set_session(
        {
            "name": FORM["name"],
            "password": FORM["password"],
            "token": token,
            "new_mons": new_mons,
            "haigou1": haigou1,
            "haigou2": haigou2,
        }
    )

    sub_def.header()
    print(html)
    sub_def.footer()
