# omiai_baby.py お見合い結果のモンスター受け取り処理

from typing import NoReturn

from sub_def.file_ops import (
    open_omiai_list,
    save_omiai_list,
    open_user_all,
    save_user_all,
)
from sub_def.utils import error, success


def omiai_baby_get(FORM: dict) -> NoReturn:
    """お見合いで生まれたモンスターをパーティに受け取る処理"""
    session = FORM.get("s", {})
    user_name = session.get("in_name")

    if not user_name:
        error("ユーザー名が取得できませんでした。", jump="top")

    omiai_list = open_omiai_list()

    # 二重送信などで既にデータが存在しない場合の安全対策
    if user_name not in omiai_list:
        error("受け取るモンスターがいません。", jump="omiai_room")

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

    # お見合いエントリのコピーを取得し、パーティ用に不要フィールドを削除する。
    # コピーを使うことで omiai_list 内のオブジェクトに影響を与えず意図を明確にする。
    new_mob = omiai_list[user_name].copy()
    for field in ["mes", "cancel", "request", "baby", "pass"]:
        new_mob.pop(field, None)

    mob_name = new_mob.get("name", "モンスター")

    # お金の減算・パーティへの追加・お見合いリストから削除
    user["money"] -= nedan
    party.append(new_mob)
    del omiai_list[user_name]

    # パーティの番号(no)を振り直し
    for i, pt in enumerate(party, 1):
        pt["no"] = i

    # データを更新して一括保存
    all_data["user"] = user
    all_data["party"] = party
    save_user_all(all_data, user_name)
    save_omiai_list(omiai_list)

    success(f"{mob_name}をパーティに加えました。", jump="my_page")
