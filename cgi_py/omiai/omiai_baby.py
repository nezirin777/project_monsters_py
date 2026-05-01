# omiai_baby.py お見合い結果のモンスター受け取り処理。


from sub_def.file_ops import (
    open_omiai_list,
    save_omiai_list,
    open_user_all,
    save_user_all,
)
from sub_def.utils import error, success


def omiai_baby_get(FORM):
    session = FORM.get("s", {})
    user_name = session.get("in_name")

    omiai_list = open_omiai_list()

    # 二重送信などで既にデータが存在しない場合の安全対策
    if user_name not in omiai_list:
        error("受け取るモンスターがいません。", jump="omiai_room")

    # 新方式：user_all で一括取得
    all_data = open_user_all(user_name)
    user = all_data.get("user", {})
    party = all_data.get("party", [])

    if len(party) >= 10:
        error(
            "パーティがいっぱいで連れていくことができませんでした。", jump="omiai_room"
        )

    nedan = omiai_list[user_name].get("hai", 0) * 5000
    if user.get("money", 0) < nedan:
        error("受け取るためのお金が足りません", jump="omiai_room")

    # お金の減算とモンスター追加処理
    user["money"] -= nedan
    new_mob = omiai_list[user_name]

    # 不要なフィールドの削除
    for field in ["mes", "cancel", "request", "baby", "pass"]:
        new_mob.pop(field, None)

    party.append(new_mob)

    # お見合いリストから自分のデータを削除
    del omiai_list[user_name]

    # パーティの番号(no)を振り直し
    for i, pt in enumerate(party, 1):
        pt["no"] = i

    # データを更新して一括保存
    all_data["user"] = user
    all_data["party"] = party
    save_user_all(all_data, user_name)

    save_omiai_list(omiai_list)

    # フラッシュメッセージを出してマイページへリダイレクト
    mes = f"{new_mob.get('name', 'モンスター')}をパーティに加えました。"
    success(mes, jump="my_page")
