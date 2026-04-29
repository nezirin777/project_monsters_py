# m_get.py - モンスターを仲間にする処理

import datetime

from sub_def.file_ops import open_user_all, save_user_all, open_battle
from sub_def.monster_ops import monster_select
from sub_def.utils import error, success, print_html
import conf


def m_get(FORM):
    Conf = conf.Conf

    token = FORM["token"]
    user_name = FORM["s"]["in_name"]

    # user_all で全データを一括取得
    all_data = open_user_all(user_name)
    party = all_data["party"]
    battle = open_battle()  # battleはまだ個別

    teki = battle["teki"][0]
    get_name = teki["name"]
    Asex = teki["sex"]

    # タイムチェック
    # エポック秒に変換してからでないと比較できない
    next_t = float(FORM["c"]["next_t"])
    current_time = datetime.datetime.now().timestamp()

    if next_t + 30 < current_time:
        error("タイムオーバーのため さみしく帰っていった")
        return

    new_mob = monster_select(get_name)
    new_mob["sex"] = Asex

    if len(party) < 10:
        party.append(new_mob)

        # noを振り直し
        for i, pt in enumerate(party, 1):
            pt["no"] = i

        all_data["party"] = party
        save_user_all(all_data, user_name)

        success(f"<span>{get_name}</span>が仲間に加わりました", jump="my_page")

    else:
        content = {
            "Conf": Conf,
            "get_name": get_name,
            "Asex": Asex,
            "party": party,
            "token": token,
        }

        print_html("monster_bye_tmp.html", content)
