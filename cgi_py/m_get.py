# m_get.py - モンスターを仲間にする処理

import datetime

from sub_def.file_ops import open_user_all, save_user_all, open_battle
from sub_def.monster_ops import monster_select
from sub_def.utils import error, success
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
    get_name, Asex = teki["name"], teki["sex"]

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
        for i, pt in enumerate(party, 1):
            pt["no"] = i

        all_data["party"] = party
        save_user_all(all_data, user_name)
        success(f"<span>{get_name}</span>が仲間に加わりました", jump="my_page")

    else:
        # モンスターリスト生成
        options = "".join(
            f'<option value="{i}">0{i}: {pt["name"]} {pt["sex"]} LV-{pt["lv"]} 配合{pt["hai"]}回</option>'
            for i, pt in enumerate(party, 1)
        )

        html = f"""
            <div class="mget_text">モンスターが一杯です。<br>誰を仲間から外しますか？</div>
            <form name=img_change method="post">
                <select name="Mno" onchange="change_img('Mno', 'img1', false)">
                    <option value=0 SELECTED>新しいモンスター : {get_name} {Asex}</option>
                    {options}
                </select>
                <button type="submit">仲間から外す</button>
                <input type="hidden" name="mode" value="m_bye">
                <input type="hidden" name="token" value="{token}">
                <br>
                <img name="img1" src="{Conf["imgpath"]}/{get_name}.gif">
            </form>
        """
