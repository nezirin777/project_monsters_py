# omiai_touroku.py - お見合い所への登録処理


from sub_def.file_ops import (
    open_omiai_list,
    save_omiai_list,
    open_user_all,
    save_user_all,
)
from sub_def.utils import error, success

import conf

Conf = conf.Conf


def omiai_touroku(FORM):
    """お見合い所に自分のモンスターを登録する処理"""
    session = FORM.get("s", {})
    user_name = session.get("in_name")

    if not user_name:
        error("ユーザー名が取得できませんでした。", "top")

    omiai = FORM.get("omiai")
    mes = FORM.get("mes", "")

    if not omiai:
        error("モンスター番号が指定されていません", jump="omiai_room")

    try:
        no = int(omiai) - 1
        if no < 0:
            raise ValueError
    except ValueError:
        error("無効なモンスター番号が指定されました", jump="omiai_room")

    # 新方式: user_allでの取得
    all_data = open_user_all(user_name)
    party = all_data.get("party", [])
    omiai_list = open_omiai_list()

    if len(party) <= 1:
        error(
            "パーティーに1体しかいない場合、お見合いに参加させることはできません",
            jump="omiai_room",
        )

    # 指定された番号のモンスターが確実に存在するかチェック
    if no >= len(party):
        error("指定されたモンスターがパーティにいません。", jump="omiai_room")

    if party[no].get("lv", 0) < Conf["haigoulevel"]:
        error("お見合い可能Lvに達していないため登録できません。", jump="omiai_room")

    # モンスター情報の移動とフィールド追加
    omiai_list[user_name] = party[no].copy()
    omiai_list[user_name].update({"mes": mes, "cancel": "", "request": "", "baby": ""})

    txt = f"{party[no].get('name', 'モンスター')}を登録しました。"

    # パーティから削除して番号(no)を振り直し
    del party[no]
    for i, pt in enumerate(party, 1):
        pt["no"] = i

    # データ更新と保存
    all_data["party"] = party
    save_user_all(all_data, user_name)
    save_omiai_list(omiai_list)

    # マイページへフラッシュメッセージ付きで遷移
    success(txt, jump="omiai_room")


def omiai_touroku_cancel(FORM):
    """お見合い所に登録したモンスターを取り下げる処理"""
    session = FORM.get("s", {})
    user_name = session.get("in_name")
    target = FORM.get("target")

    if not user_name or not target:
        error("必要な情報が指定されていません。", jump="omiai_room")

    # 新方式: user_allでの取得
    all_data = open_user_all(user_name)
    party = all_data.get("party", [])
    omiai_list = open_omiai_list()

    omiai = omiai_list.get(user_name)
    if not omiai:
        error("指定されたお見合い情報が存在しません", jump="omiai_room")

    # 申請中のチェック
    if omiai.get("request"):
        error(
            "他のユーザーに申請を出している場合、登録をキャンセルできません。<br>まずは申請を取り下げてください。",
            jump="omiai_room",
        )

    # 申請されている場合のチェック
    for v in omiai_list.values():
        if v.get("request") == target:
            error(
                "あなたへのお見合い申請がある場合、登録をキャンセルできません。<br>申請の対応を行ってください。",
                jump="omiai_room",
            )

    if len(party) >= 10:
        error(
            "パーティがいっぱいで連れていくことができませんでした。", jump="omiai_room"
        )

    # 不要なフィールドを削除してパーティに戻す
    for field in ["mes", "cancel", "request", "baby"]:
        omiai.pop(field, None)

    party.append(omiai)

    txt = f"{omiai.get('name', 'モンスター')}をパーティに加えました。"

    # パーティの番号(no)を振り直し
    for i, pt in enumerate(party, 1):
        pt["no"] = i

    del omiai_list[user_name]

    # データ更新と保存
    all_data["party"] = party
    save_user_all(all_data, user_name)
    save_omiai_list(omiai_list)

    # マイページへフラッシュメッセージ付きで遷移
    success(txt, jump="omiai_room")
