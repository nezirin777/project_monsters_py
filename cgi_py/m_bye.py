# m_bye.py - パーティからモンスターを削除し、新しいモンスターを追加する関数

from sub_def.file_ops import open_user_all, save_user_all, open_battle
from sub_def.monster_ops import monster_select
from sub_def.utils import error, success


def m_bye(FORM):
    Mno = int(FORM["Mno"])
    user_name = FORM["s"]["in_name"]

    # user_all で全データを一括取得
    all_data = open_user_all(user_name)
    party = all_data["party"]
    battle = open_battle()  # battleはまだ個別

    teki = battle["teki"][0]
    get_name, Asex = teki["name"], teki["sex"]

    # メッセージの初期設定
    if Mno == 0:
        message = f"<span>{get_name}</span>はさみしそうにさっていった"
    else:
        # 配列位置調整
        try:
            Mno -= 1
            by_name = party[Mno]["name"]
            party.pop(Mno)

            # 新しいモンスターを追加
            new_mob = monster_select(get_name)
            new_mob["sex"] = Asex
            party.append(new_mob)

            # パーティ番号の再設定
            for i, pt in enumerate(party, 1):
                pt["no"] = i

            message = (
                f"<span>{get_name}</span>が加わり<span>{by_name}</span>はさっていった"
            )
        except IndexError:
            error("無効なモンスター番号が指定されました")
            return

    # 更新と結果表示（partyをuser_allに反映）
    all_data["party"] = party
    save_user_all(all_data, user_name)  # user_nameを明示的に渡す

    success(message, jump="my_page")
