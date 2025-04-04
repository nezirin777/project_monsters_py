from jinja2 import Environment, FileSystemLoader

import sub_def
import conf

Conf = conf.Conf


def haigou_hensin(FORM):
    """配合による新モンスター生成と表示"""
    new_m = FORM["s"]["new_mons"].replace("フィッシュル(制服)", "フィッシュル")
    # 配列位置に合わせ-1されたものを引き継いでいるのでそのままで大丈夫
    haigou1, haigou2 = int(FORM["s"]["haigou1"]), int(FORM["s"]["haigou2"])

    user = sub_def.open_user()
    party = sub_def.open_party()

    hai_A = party[haigou1]
    hai_B = party[haigou2]

    cost = (hai_A["lv"] + hai_B["lv"]) * 10

    # ユーザーのお金を更新
    user["money"] -= cost
    sub_def.save_user(user)

    # 新モンスター生成
    mlv = int(hai_A["lv"] + hai_B["lv"])
    new_hai = hai_A["hai"] + hai_B["hai"] + 1
    hosei = max(new_hai // 2, 1)

    new_mob = sub_def.monster_select(new_m, hosei, 1)
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

    sub_def.save_party(party)

    # HTML生成
    # Jinja2の環境設定とテンプレートファイルの読み込み
    env = Environment(
        loader=FileSystemLoader("templates"), cache_size=100
    )  # テンプレートディレクトリ
    template = env.get_template("new_monster_tmp.html")
    html = template.render(Conf=Conf, my_data=new_mob, token="", mode="")

    sub_def.header()
    print(html)
    sub_def.my_page_button(FORM["token"])
