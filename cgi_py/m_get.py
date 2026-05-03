# m_get.py - モンスターを仲間にする処理

import datetime

from sub_def.file_ops import open_user_all, save_user_all, open_battle
from sub_def.monster_ops import monster_select
from sub_def.utils import error, success, print_html
import conf

Conf = conf.Conf


def m_get(FORM):

    # セッション情報の安全な取得
    session = FORM.get("s", {})
    token = session.get("token", "")
    user_name = session.get("in_name")

    # user_all で全データを一括取得
    all_data = open_user_all(user_name)
    user = all_data.get("user", {})
    party = all_data.get("party", [])

    # attleデータを開く際に user_name を引数として渡す
    battle = open_battle(user_name)

    # バトルデータが破損・消失している場合のフェイルセーフ
    if not battle or not battle.get("teki"):
        error(
            "戦闘データが見つかりません。<br>最初からやり直してください。",
            jump="my_page",
        )

    # teki[0] に仲間になるモンスター情報が入っている前提
    teki = battle["teki"][0]
    get_name = teki.get("name", "")
    Asex = teki.get("sex", "陰")

    if not get_name:
        error("仲間にするモンスターの情報がありません。", jump="my_page")

    # タイムチェック
    # エポック秒に変換してからでないと比較できない
    try:
        # セッション または ユーザーデータから next_t を安全に取得
        next_t_val = FORM.get("s", {}).get("next_t") or user.get("next_t", 0)
        next_t = float(next_t_val)
    except (ValueError, TypeError):
        next_t = 0.0

    current_time = datetime.datetime.now().timestamp()

    # 制限時間（30秒）を過ぎていた場合
    if next_t + 30 < current_time:
        error("タイムオーバーのため さみしく帰っていった", jump="my_page")

    # 新しいモンスターを生成
    new_mob = monster_select(get_name)
    new_mob["sex"] = Asex

    # パーティ上限チェック
    if len(party) < 10:
        party.append(new_mob)

        # noを振り直し
        for i, pt in enumerate(party, 1):
            pt["no"] = i

        all_data["party"] = party
        save_user_all(all_data, user_name)

        success(f"<span>{get_name}</span>が仲間に加わりました", jump="my_page")

    else:
        # パーティが一杯の場合は入れ替え画面（monster_bye_tmp.html）へ
        content = {
            "Conf": Conf,
            "get_name": get_name,
            "Asex": Asex,
            "party": party,
            "token": token,
        }

        print_html("monster_bye_tmp.html", content)
