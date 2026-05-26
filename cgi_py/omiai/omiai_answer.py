# omiai_answer.py お見合い依頼に対する処理

from typing import NoReturn

import conf
from cgi_py.haigou_check import haigou_sub
from sub_def.file_ops import open_omiai_list, save_omiai_list, open_user_all
from sub_def.utils import print_html, slim_number_with_cookie, error, success
from sub_def.monster_ops import monster_select

Conf = conf.Conf


def omiai_answer_no(FORM: dict) -> NoReturn:
    """お見合いをお断りする処理"""
    session = FORM.get("s", {})
    user_name = session.get("in_name")
    target = FORM.get("target")

    if not user_name or not target:
        error("必要な情報が指定されていません。", jump="omiai_room")

    omiai_list = open_omiai_list()

    # 相手の申請をキャンセル状態に更新。
    # すでに相手のデータが消えている場合（期限切れ等）はスキップして成功扱いにする。
    if target in omiai_list:
        omiai_list[target]["request"] = ""
        omiai_list[target][
            "cancel"
        ] = f"{user_name}さんへの依頼はお断りされてしまったようです・・・"
        save_omiai_list(omiai_list)

    success(f"{target}さんからの申し込みをお断りしました。", jump="omiai_room")


def omiai_answer_ok(FORM: dict) -> NoReturn:
    """お見合いを受ける（確認画面表示）処理"""
    session = FORM.get("s", {})
    user_name = session.get("in_name")
    target = FORM.get("target")
    token = session.get("token")

    if not user_name or not target:
        error("必要な情報が指定されていません。", jump="omiai_room")

    omiai_list = open_omiai_list()

    # 自身や相手のデータが消失していないかチェック（二重送信・期限切れ対策）
    if user_name not in omiai_list or target not in omiai_list:
        error("お見合いデータが見つかりません。", jump="omiai_room")

    # 自分が他の人に申請中の場合は受けられない
    if omiai_list[user_name].get("request"):
        error(
            "あなたは他の人に申請中です。<br>この人とお見合いするには申請を取り下げる必要があります。",
            jump="omiai_room",
        )

    nameA = omiai_list[user_name]["name"]
    nameB = omiai_list[target]["name"]

    # haigou_sub はタプル(モンスター名, ヒントフラグ)を返す
    my_new_mons, hint_flag = haigou_sub(nameA, nameB, 1)

    # 図鑑に登録済みであれば名前を表示、未登録なら「？？？」に伏せる
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

    print_html("haigou_check_tmp.html", content)


def omiai_get_monster(data: dict, new_mons: str) -> dict:
    """新しいお見合い産モンスターを生成するヘルパー関数"""
    mlv = data.get("lv", 1) + 10
    new_hai = data.get("hai", 0) + 1
    hosei = max(new_hai // 2, 1)

    new_mob = monster_select(new_mons, hosei)
    new_mob.update({"lv": 1, "mlv": mlv, "hai": new_hai})

    return new_mob


def omiai_answer_result(FORM: dict) -> NoReturn:
    """お見合いを確定させ、モンスターを更新する処理"""
    session = FORM.get("s", {})
    user_name = session.get("in_name")
    target = FORM.get("target")
    token = session.get("token")

    if not user_name or not target:
        error("必要な情報が指定されていません。", jump="omiai_room")

    omiai_list = open_omiai_list()

    if user_name not in omiai_list or target not in omiai_list:
        error("お見合いデータが見つかりません。", jump="omiai_room")

    # 自分または相手に申請していた第三者の申請をすべてキャンセルする。
    # request_target を先に取り出してから request を "" にクリアする。
    # ループ変数 omiai は omiai_list[name] と同一オブジェクトなので、
    # クリア後に omiai.get("request") を参照すると "" になりメッセージが壊れるため注意。
    for name, omiai in list(omiai_list.items()):
        request_target = omiai.get("request")
        if request_target in (user_name, target):
            omiai["request"] = ""
            omiai["cancel"] = (
                f"{request_target}さんへの依頼はお断りされてしまったようです・・・"
            )

    my_data = omiai_list[user_name]
    target_data = omiai_list[target]

    # 双方が受け取るモンスター名を取得（hint_flag はここでは不要）
    my_new_mons_name, _ = haigou_sub(my_data["name"], target_data["name"], 1)
    target_new_mons_name, _ = haigou_sub(target_data["name"], my_data["name"], 1)

    my_new_mons = omiai_get_monster(my_data, my_new_mons_name)
    target_new_mons = omiai_get_monster(target_data, target_new_mons_name)

    # 両者のデータを一気に更新
    for user_data, new_mons, partner_name in [
        (my_data, my_new_mons, target),
        (target_data, target_new_mons, user_name),
    ]:
        user_data.update(new_mons)
        user_data.update(
            {"mes": f"{partner_name}さんとのお見合いが成功しました。", "baby": 1}
        )

    save_omiai_list(omiai_list)

    my_data_v = slim_number_with_cookie(my_data)

    content = {
        "Conf": Conf,
        "my_data": my_data_v,
        "token": token,
        "mode": "omiai_room",
    }

    print_html("new_monster_tmp.html", content)
