# haigou_check.py - 配合チェック

from sub_def.utils import error, print_html
from sub_def.file_ops import open_monster_dat, open_user_all
from sub_def.crypto import set_session, get_session
import conf

Conf = conf.Conf


def haigou_sub(base, aite, flg=0):
    # base 及び aite はモンスター名
    # 特殊名の変換
    base, aite = [
        name if name != "フィッシュル(制服)" else "フィッシュル"
        for name in (base, aite)
    ]

    M_list = open_monster_dat()
    base_type = M_list[base]["m_type"]
    aite_type = M_list[aite]["m_type"]

    best = None
    best_rank = 999  # 小さいほど優先度高い
    hint_flag = False  # 特殊条件のヒント獲得フラグ

    # 条件を満たす新モンスターを検索
    for name, mon in M_list.items():

        if int(mon["omiai_only"] or 0) == 1 and flg == 0:
            continue  # お見合い限定は通常配合では出現しない

        for n in range(1, 4):
            blood = mon[f"血統{n}"]
            partner = mon[f"相手{n}"]

            # 特殊条件に対するヒント獲得
            if mon["room"] == "異世界":
                if base == blood or aite == partner:
                    hint_flag = True

            # 個体×個体
            if base == blood and aite == partner:
                return name, hint_flag  # 最優先なので即返す

            # 系統×個体
            if (base_type == blood and aite == partner) or (
                base == blood and aite_type == partner
            ):
                if best_rank > 2:
                    best = name
                    best_rank = 2
                continue

            # 系統×系統
            if base_type == blood and aite_type == partner:
                if best_rank > 3:
                    best = name
                    best_rank = 3

    return (best if best else base), hint_flag


def haigou_check(FORM):
    """配合チェック処理（user_all 新形式完全対応）"""
    # 配列位置に合わせ-1
    haigou1 = int(FORM["haigou1"]) - 1
    haigou2 = int(FORM["haigou2"]) - 1

    user_name = FORM["s"]["in_name"]
    token = FORM["token"]

    if haigou1 < 0 or haigou2 < 0:
        error("正しく設定されていません-1")
    if haigou1 == haigou2:
        error("正しく設定されていません-2")

    # 新形式：user_all で一括取得
    all_data = open_user_all(user_name)
    user = all_data["user"]
    party = all_data["party"]
    zukan = all_data["zukan"]

    hai_A = party[haigou1]
    hai_B = party[haigou2]

    if hai_A["sex"] == hai_B["sex"]:
        error("陰陽が同じで配合出来ません")

    if any(hai["lv"] < Conf["haigoulevel"] for hai in (hai_A, hai_B)):
        error(
            f"<img src={Conf['imgpath']}/{hai_A['name']}.gif>または<img src={Conf['imgpath']}/{hai_B['name']}.gif>のレベルが{Conf['haigoulevel']}に達していません"
        )

    if user["money"] < (hai_A["lv"] + hai_B["lv"]) * 10:
        error("お金が足りません")

    new_mons, hint_flag = haigou_sub(hai_A["name"], hai_B["name"])

    # 図鑑登録済みかどうかチェック
    if new_mons in zukan and zukan[new_mons].get("get", 0) == 1:
        new_mons_name = new_mons
        hint_flag = False
    else:
        new_mons_name = "？？？"

    # セッションに配合情報を保存
    session = get_session()
    session.update(
        {
            "new_mons": new_mons,
            "haigou1": haigou1,
            "haigou2": haigou2,
            "hint_flag": hint_flag,
            "new_mons_name": new_mons_name,
        }
    )
    set_session(session)

    content = {
        "Conf": Conf,
        "token": token,
        "nameA": hai_A["name"],
        "nameB": hai_B["name"],
        "my_new_mons": new_mons_name,
        "target": "",
        "mode": "haigou",
        "hint_flag": hint_flag,
    }

    print_html("haigou_check_tmp.html", content)
