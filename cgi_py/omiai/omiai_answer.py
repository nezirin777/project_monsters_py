# omiai_answer.py お見合い依頼に対する処理

from cgi_py.haigou_check import haigou_sub
from sub_def.file_ops import open_omiai_list, save_omiai_list, open_user_all
from sub_def.utils import print_html, slim_number_with_cookie, error, success
from sub_def.monster_ops import monster_select

import conf

Conf = conf.Conf


def omiai_answer_no(FORM):
    """お見合いをお断りする処理"""
    session = FORM.get("s", {})
    user_name = session.get("in_name")
    target = FORM.get("target")

    omiai_list = open_omiai_list()

    # 相手の申請をキャンセル状態に更新
    if target in omiai_list:
        omiai_list[target]["request"] = ""
        omiai_list[target][
            "cancel"
        ] = f"{user_name}さんへの依頼はお断りされてしまったようです・・・"
        save_omiai_list(omiai_list)

    # 成功メッセージを出してマイページ等へリダイレクト（フラッシュメッセージ機能を利用）
    success(f"{target}さんからの申し込みをお断りしました。", jump="omiai_room")


def omiai_answer_ok(FORM):
    """お見合いを受ける（確認画面表示）処理"""
    session = FORM.get("s", {})
    user_name = session.get("in_name")
    target = FORM.get("target")
    token = session.get("token")

    omiai_list = open_omiai_list()

    # 自分が他の人に申請中の場合は受けられない
    if omiai_list.get(user_name, {}).get("request"):
        error(
            "あなたは他の人に申請中です。<br>この人とお見合いするには申請を取り下げる必要があります。",
            jump="omiai_room",
        )

    nameA = omiai_list[user_name]["name"]
    nameB = omiai_list[target]["name"]

    # 生まれるモンスターの判定 (フラグ=1: お見合い限定モンスターも許可)
    # haigou_subはタプル(モンスター名, ヒントフラグ)を返す
    my_new_mons, hint_flag = haigou_sub(nameA, nameB, 1)

    # 新方式：user_allから図鑑データを取得して判明しているかチェック
    user_all = open_user_all(user_name)
    zukan = user_all.get("zukan", {})

    if my_new_mons not in zukan or not zukan[my_new_mons].get("get"):
        my_new_mons = "？？？"
    else:
        hint_flag = False  # すでに知っているモンスターならヒントは出さない

    content = {
        "Conf": Conf,
        "nameA": nameA,
        "nameB": nameB,
        "my_new_mons": my_new_mons,
        "target": target,
        "token": token,
        "mode": "omiai_ans",
        "hint_flag": hint_flag,
    }

    # テンプレートに丸投げ
    print_html("haigou_check_tmp.html", content)


def omiai_get_monster(data, new_mons, user_name):
    """新しいモンスターを生成するヘルパー関数"""
    mlv = data.get("lv", 1) + 10
    new_hai = data.get("hai", 0) + 1
    hosei = max(int(new_hai / 2), 1)

    # monster_selectを使って基本ステータスを生成
    new_mob = monster_select(new_mons, hosei, 1, user_name)
    new_mob.update({"lv": 1, "mlv": mlv, "hai": new_hai})

    return new_mob


def omiai_answer_result(FORM):
    """お見合いを確定させ、モンスターを更新する処理"""
    session = FORM.get("s", {})
    user_name = session.get("in_name")
    target = FORM.get("target")
    token = session.get("token")

    omiai_list = open_omiai_list()

    # 自分、あるいは相手に対する他のリクエストをすべてキャンセル処理する
    for name, omiai in omiai_list.items():
        if omiai.get("request") in (user_name, target):
            omiai_list[name]["request"] = ""
            omiai_list[name][
                "cancel"
            ] = f"{omiai.get('request')}さんへの依頼はお断りされてしまったようです・・・"

    my_data = omiai_list[user_name]
    target_data = omiai_list[target]

    # 双方が受け取るモンスター名を取得（hint_flagはここでは捨てる）
    my_new_mons_name, _ = haigou_sub(my_data["name"], target_data["name"], 1)
    target_new_mons_name, _ = haigou_sub(target_data["name"], my_data["name"], 1)

    # モンスターデータの生成
    my_new_mons = omiai_get_monster(my_data, my_new_mons_name, user_name)
    target_new_mons = omiai_get_monster(target_data, target_new_mons_name, target)

    # 両者のデータを一気に更新
    for user_data, new_mons, partner_name in [
        (my_data, my_new_mons, target),
        (target_data, target_new_mons, user_name),
    ]:
        user_data.update(new_mons)
        user_data.update(
            {"mes": f"{partner_name}さんとのお見合いが成功しました。", "baby": 1}
        )

    # 保存
    save_omiai_list(omiai_list)

    # 表示用にフォーマット
    my_data_v = slim_number_with_cookie(my_data)

    content = {
        "Conf": Conf,
        "my_data": my_data_v,
        "token": token,
        "mode": "omiai_room",
    }

    print_html("new_monster_tmp.html", content)
