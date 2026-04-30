# omiai_request.py - お見合い申請処理

from cgi_py.haigou_check import haigou_sub
from sub_def.file_ops import open_omiai_list, save_omiai_list, open_user_all
from sub_def.utils import print_html, error, success

import conf

Conf = conf.Conf


def omiai_request(FORM):
    """お見合いを申し込む前の確認画面を表示する"""
    session = FORM.get("s", {})
    user_name = session.get("in_name")
    target = FORM.get("target")
    token = session.get("token")

    # お見合いリストからデータを取得
    omiai_list = open_omiai_list()
    my_data = omiai_list.get(user_name)
    target_data = omiai_list.get(target)

    # 自モンスターを登録済みかチェック
    if not my_data:
        error(
            "あなたはまだ未登録です。<br>登録してから申請してください",
            jump="omiai_room",
        )

    # すでに申請がないかチェック
    if my_data.get("request"):
        error(
            "申請できるのは1人までです。<br>他の人に申請したい場合は申請をキャンセルしてからどうぞ。",
            jump="omiai_room",
        )

    # 相手が存在するかチェック（二重送信・削除対策）
    if not target_data:
        error("対象のユーザー・モンスターが見つかりません。", jump="omiai_room")

    # 申請相手から依頼が来てないかチェック
    if target_data.get("request") == user_name:
        error(f"{target}さんからはすでに依頼が来てます。", jump="omiai_room")

    # 性別チェック
    if my_data.get("sex") == target_data.get("sex"):
        error("性別が同じ為お見合いができません。", jump="omiai_room")

    # モンスターの名前を取得し、配合結果をチェック
    nameA = my_data["name"]
    nameB = target_data["name"]

    # haigou_subはタプル(モンスター名, ヒントフラグ)を返す
    my_new_mons, hint_flag = haigou_sub(nameA, nameB, 1)

    # 新方式：user_allから図鑑データを取得して判明しているかチェック
    user_all = open_user_all(user_name)
    zukan = user_all.get("zukan", {})

    # 図鑑未登録の場合は「？？？」を表示
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
        "mode": "omiai_req",
        "hint_flag": hint_flag,
    }

    print_html("haigou_check_tmp.html", content)


def omiai_request_ok(FORM):
    """お見合い申請を確定させる処理"""
    session = FORM.get("s", {})
    user_name = session.get("in_name")
    target = FORM.get("target")

    omiai_list = open_omiai_list()

    # 安全対策：自身や相手のデータが消失していないかチェック
    if user_name not in omiai_list or target not in omiai_list:
        error("お見合いデータが見つかりません。", jump="omiai_room")

    # 自分に申請記録を保存
    omiai_list[user_name]["request"] = target
    request_monster = omiai_list[target].get("name", "モンスター")

    save_omiai_list(omiai_list)

    # フラッシュメッセージを出してマイページへ戻る
    success(
        f"{target}さんの{request_monster}にお見合いを申請しました。", jump="omiai_room"
    )


def omiai_request_cancel(FORM):
    """お見合い申請をキャンセルする処理"""
    session = FORM.get("s", {})
    user_name = session.get("in_name")
    target = FORM.get("target")

    omiai_list = open_omiai_list()

    # 自分の申請状態を空にする
    if user_name in omiai_list:
        omiai_list[user_name]["request"] = ""
        save_omiai_list(omiai_list)

    # フラッシュメッセージを出してマイページへ戻る
    success(f"{target}さんへの申請を取り消しました。", jump="omiai_room")
