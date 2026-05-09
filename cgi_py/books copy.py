# books.py 本屋(性格変更)処理

from sub_def.utils import error, success, print_html, get_and_clear_flash
from sub_def.file_ops import (
    open_user_all,
    save_user_all,
    open_book_dat,
    open_seikaku_dat,
)
import conf

Conf = conf.Conf
BOOK_PRICE = 1000  # 本の価格
SEIKAKU_MAX = 3  # 性格のパラメータ最大値
SEIKAKU_MIN = 1  # 性格のパラメータ最小値


def books(FORM):
    """本屋（性格変更）画面表示"""
    user_name = FORM["s"]["in_name"]
    token = FORM["s"]["token"]

    # Flashメッセージの取得とクリア（一番最初に呼ぶ）
    flash_msg, flash_type = get_and_clear_flash(FORM["s"])

    # 新形式でパーティを取得
    all_data = open_user_all(user_name)
    party = all_data.get("party", [])

    # モンスター表示用データ
    monster_data = [
        {
            "no": pt["no"],
            "img": f'{Conf["imgpath"]}/{pt["name"]}.gif',
            "name": pt["name"],
            "sex": pt["sex"],
            "sei": pt["sei"],
        }
        for pt in party
    ]

    # セレクトボックス用
    monster_options = [
        {
            "value": i,
            "label": f'{pt["no"]}-{pt["name"]}',
        }
        for i, pt in enumerate(party)
    ]

    Book_dat = open_book_dat()
    book_options = list(Book_dat.keys())

    content = {
        "Conf": Conf,
        "token": token,
        "monster_data": monster_data,
        "monster_options": monster_options,
        "book_options": book_options,
        "book_price": BOOK_PRICE,
        "flash_msg": flash_msg,
        "flash_type": flash_type,
    }

    print_html("book_tmp.html", content)


def book_read(FORM):
    """本を読み、性格を変更する処理"""
    try:
        Mno = int(FORM["Mno"])
        Bname = FORM["Bname"]
    except (ValueError, KeyError):
        error("モンスターまたは本が選択されていません", jump="books")

    user_name = FORM["s"]["in_name"]

    all_data = open_user_all(user_name)
    user = all_data.get("user", {})
    party = all_data.get("party", [])

    Book_dat = open_book_dat()
    seikaku = open_seikaku_dat()

    # ★安全対策: 念のため送られてきたインデックスが範囲内かチェック
    if not (0 <= Mno < len(party)):
        error("不正なモンスターが選択されました", jump="books")

    if user.get("money", 0) < BOOK_PRICE:
        error("お金が足りません", jump="my_page")

    # お金消費
    user["money"] -= BOOK_PRICE

    Msei = party[Mno]["sei"]
    Newsei = Msei  # 性格が変わらない場合の初期値

    # 新しい性格パラメータを計算
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

    # 既存の性格データと一致するものを探す
    for name, traits in seikaku.items():
        if all(traits[key] == new_traits[key] for key in new_traits):
            Newsei = name
            break

    # 性格の変更を反映
    party[Mno]["sei"] = Newsei

    # 保存（すべて user_all にまとめて1回だけ）
    all_data["user"] = user
    all_data["party"] = party
    save_user_all(all_data, user_name)

    # 結果メッセージ
    if Msei != Newsei:
        mes = f"{party[Mno]['name']}の性格が<br>【{Msei}】から【{Newsei}】に変わった"
    else:
        mes = f"{party[Mno]['name']}の性格は変わらなかった"

    success(mes, jump="books")
