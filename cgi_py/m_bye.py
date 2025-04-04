import sub_def


def m_bye(FORM):
    """パーティからモンスターを削除し、新しいモンスターを追加する関数"""
    Mno = int(FORM["Mno"])

    party = sub_def.open_party()
    battle = sub_def.open_battle()

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
            new_mob = sub_def.monster_select(get_name)
            new_mob["sex"] = Asex
            party.append(new_mob)

            # パーティ番号の再設定
            for i, pt in enumerate(party, 1):
                pt["no"] = i

            message = (
                f"<span>{get_name}</span>が加わり<span>{by_name}</span>はさっていった"
            )
        except IndexError:
            sub_def.error("無効なモンスター番号が指定されました")
            return

    # 更新と結果表示
    sub_def.save_party(party)
    sub_def.result(message, "", FORM["token"])
