from sub_def.utils import error, print_html, print_result
from sub_def.file_ops import (
    open_user,
    open_party,
    open_book_dat,
    open_seikaku_dat,
    save_party,
    save_user,
)
import conf

Conf = conf.Conf
BOOK_PRICE = 1000  # 本の価格
SEIKAKU_MAX = 3  # 性格のパラメータ最大値
SEIKAKU_MIN = 1  # 性格のパラメータ最小値


def books(FORM):
    token = FORM["token"]
    party = open_party()

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

    # セレクト用
    monster_options = [
        {
            "value": pt["no"],
            "label": f'{pt["no"]}-{pt["name"]}',
        }
        for pt in party
    ]

    # 本リスト
    books_list = [
        "ぼうけんたん",
        "こわいはなしのほん",
        "やさしくなれるほん",
        "ずるっこのほん",
        "あたまがさえるほん",
        "ユーモアのほん",
    ]

    mes = (
        "モンスターに本を読ませると性格が変わります。<br>"
        "現在の性格によっては変わらない場合もあります。<br>"
        f"1冊{BOOK_PRICE}G。"
    )

    content = {
        "Conf": Conf,
        "token": token,
        "monster_data": monster_data,
        "monster_options": monster_options,
        "books_list": books_list,
        "mes": mes,
    }

    print_html("book_tmp.html", content)


def book_read(FORM):

    try:
        Mno = int(FORM["Mno"]) - 1  # 配列位置に合わせるため -1
        Bname = FORM["Bname"]
    except (ValueError, KeyError):
        error("モンスターまたは本が選択されていません")

    token = FORM["token"]

    user = open_user()
    party = open_party()
    Book_dat = open_book_dat()
    seikaku = open_seikaku_dat()

    if user["money"] < BOOK_PRICE:
        error("お金が足りません")

    user["money"] -= BOOK_PRICE

    Msei = party[Mno]["sei"]
    Newsei = Msei  # 性格が変わらない場合の初期値

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

    save_user(user)
    save_party(party)

    mes = (
        f"性格が【{Msei}】から【{Newsei}】に変わった"
        if Msei != Newsei
        else "モンスターの性格は変わらなかった"
    )

    content = {
        "Conf": Conf,
        "token": token,
        "mes": mes,
        "mode": "books",
        "button_name": "本屋に戻る",
    }

    print_html("result_tmp.html", content)
