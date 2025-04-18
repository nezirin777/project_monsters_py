import sub_def
import conf
import time

Conf = conf.Conf
BOOK_PRICE = 1000  # 本の価格
SEIKAKU_MAX = 3  # 性格のパラメータ最大値
SEIKAKU_MIN = 1  # 性格のパラメータ最小値


def books(FORM):
    token = FORM["token"]
    party = sub_def.open_party()

    # モンスターの表示と選択肢
    monster_boxes = "".join(
        [
            f"""
        <div class="books_mbox1">
            <div class="books_no">{pt["no"]}</div>
            <div class="books_im"><img src="{Conf["imgpath"]}/{pt["name"]}.gif"></div>
            <div class="books_m">{pt["name"]}<br>-{pt["sex"]}-<br>{pt["sei"]}</div>
        </div>
        """
            for pt in party
        ]
    )
    monster_options = "".join(
        [
            f"""<option value="{pt["no"]}">{pt["no"]}-{pt["name"]}</option>"""
            for pt in party
        ]
    )

    # メッセージおよびフォーム生成
    mes = "モンスターに本を読ませると性格が変わります。<br>現在の性格によっては変わらない場合もあります。<br>1冊1000G。"
    html = f"""
        <div id="books_mbox">{monster_boxes}</div>
        <form action="{{ Conf.cgiurl }}" method="post">
            <div class="books_text3">モンスターを選択して下さい</div>
            <select name="Mno">{monster_options}</select>
            <div class="books_text3">本を選択して下さい</div>
            <select name="Bname">
                <option value="ぼうけんたん">ぼうけんたん</option>
                <option value="こわいはなしのほん">こわいはなしのほん</option>
                <option value="やさしくなれるほん">やさしくなれるほん</option>
                <option value="ずるっこのほん">ずるっこのほん</option>
                <option value="あたまがさえるほん">あたまがさえるほん</option>
                <option value="ユーモアのほん">ユーモアのほん</option>
            </select>
            <br><br>
            <button type="submit">本を読む</button>
            <input type="hidden" name="mode" value="book_read">
            <input type="hidden" name="token" value="{token}">
        </form>
    """

    sub_def.result(mes, html, token)


def book_read(FORM):
    """モンスターに本を読ませ、性格を変更する"""
    try:
        Mno = int(FORM["Mno"]) - 1  # 配列位置に合わせるため -1
        Bname = FORM["Bname"]
    except (ValueError, KeyError):
        sub_def.error("モンスターまたは本が選択されていません")

    token = FORM["token"]

    user = sub_def.open_user()
    party = sub_def.open_party()
    Book_dat = sub_def.open_book_dat()
    seikaku = sub_def.open_seikaku_dat()

    # お金のチェック
    if user["money"] < BOOK_PRICE:
        sub_def.error("お金が足りません")
    user["money"] -= BOOK_PRICE

    # 現在の性格情報の取得
    Msei = party[Mno]["sei"]
    Newsei = Msei  # 性格が変わらない場合の初期値

    # 新しい性格値の計算
    new_traits = {
        "勇気": min(
            SEIKAKU_MAX,
            max(SEIKAKU_MIN, seikaku[Msei]["勇気"] + Book_dat[Bname]["勇気"]),
        ),
        "優しさ": min(
            SEIKAKU_MAX,
            max(SEIKAKU_MIN, seikaku[Msei]["優しさ"] + Book_dat[Bname]["優しさ"]),
        ),
        "知性": min(
            SEIKAKU_MAX,
            max(SEIKAKU_MIN, seikaku[Msei]["知性"] + Book_dat[Bname]["知性"]),
        ),
    }

    # 新しい性格があるか判定
    for name, traits in seikaku.items():
        if all(traits[key] == new_traits[key] for key in new_traits):
            Newsei = name
            break

    # 性格の変更を反映
    party[Mno]["sei"] = Newsei
    sub_def.save_user(user)
    sub_def.save_party(party)

    # メッセージの生成
    mes = (
        f"性格が【{Msei}】から【{Newsei}】に変わった"
        if Msei != Newsei
        else "モンスターの性格は変わらなかった"
    )

    html = f"""
        <form action="{{ Conf.cgiurl }}" method="post">
            <input type="hidden" name="mode" value="books">
            <input type="hidden" name="token" value="{token}">
            <button type="submit">本屋へ戻る</button>
        </form>
    """

    sub_def.result(mes, html, token)
