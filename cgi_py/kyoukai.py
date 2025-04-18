import sub_def


def kyoukai(FORM):
    """教会でお祈りを行う準備と確認画面の表示"""
    kyoukaidai = int(FORM["kyoukaidai"])
    money = int(FORM["money"])
    token = FORM["token"]

    # エラーチェック
    if money < kyoukaidai:
        sub_def.error("お金が足りません")
    elif kyoukaidai == 0:
        sub_def.error("現在お祈りする必要はありません")

    html = f"""
        <form action="{{ Conf.cgiurl }}" method="post">
            <button type="submit">お祈りする</button>
            <input type="hidden" name="mode" value="kyoukai_ok">
            <input type="hidden" name="token" value="{token}">
        </form>
    """

    sub_def.result("お祈りしますか？", html, FORM["token"])


def recover_monster(monster):
    """モンスターのHP・MPを回復し、回復コストを計算"""
    if monster["hp"] == 0:
        monster["hp"], monster["mp"] = monster["mhp"], monster["mmp"]
        return (monster["mhp"] + monster["mmp"]) * 2
    return 0


def kyoukai_ok(FORM):
    """お祈りによりパーティのHP・MPを回復し、費用を更新"""
    user = sub_def.open_user()
    party = sub_def.open_party()

    # 回復と費用計算
    total_cost = sum(recover_monster(pt) for pt in party)

    # 所持金更新と保存
    user["money"] -= int(total_cost)
    sub_def.save_user(user)
    sub_def.save_party(party)

    sub_def.result("お祈りが天にとどきました", "", FORM["token"])
