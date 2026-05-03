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

    # 辞書に存在しない場合の安全対策として get を使用
    base_type = M_list.get(base, {}).get("m_type", "")
    aite_type = M_list.get(aite, {}).get("m_type", "")

    best = None
    best_rank = 999  # 小さいほど優先度高い
    hint_flag = False  # 特殊条件のヒント獲得フラグ

    # 条件を満たす新モンスターを検索
    for name, mon in M_list.items():

        if int(mon.get("omiai_only") or 0) == 1 and flg == 0:
            continue  # お見合い限定は通常配合では出現しない

        for n in range(1, 4):
            blood = mon.get(f"血統{n}")
            partner = mon.get(f"相手{n}")

            # 特殊条件に対するヒント獲得
            if mon.get("room") == "異世界":
                if base == blood or aite == partner:
                    hint_flag = True

            # 【最優先】個体×個体
            if base == blood and aite == partner:
                return name, hint_flag  # 最優先なので即返す

            # 【優先度2】系統×個体
            if (base_type == blood and aite == partner) or (
                base == blood and aite_type == partner
            ):
                if best_rank > 2:
                    best = name
                    best_rank = 2
                continue

            # 【優先度3】系統×系統
            if base_type == blood and aite_type == partner:
                if best_rank > 3:
                    best = name
                    best_rank = 3

    # 条件に合うモンスターがいない場合はベースモンスターを引き継ぐ
    return (best if best else base), hint_flag


def haigou_check(FORM):
    """配合チェック処理"""

    user_name = FORM["s"]["in_name"]
    token = FORM["s"]["token"]

    # 入力値の取得とエラーハンドリング（不正な値でのクラッシュを防ぐ）
    val1 = FORM.get("haigou1", "")
    val2 = FORM.get("haigou2", "")

    # 空文字や送信漏れの場合はエラー画面へ
    if not val1 or not val2:
        error("モンスターが正しく選択されていません", jump="my_page")

    try:
        # books.pyに合わせて、フォームから直接配列インデックス(0始まり)を受け取る
        haigou1 = int(val1)
        haigou2 = int(val2)
    except ValueError:
        error("モンスターが正しく選択されていません", jump="my_page")

    # 新形式：user_all で一括取得
    all_data = open_user_all(user_name)
    user = all_data.get("user", {})
    party = all_data.get("party", [])
    zukan = all_data.get("zukan", {})

    # パーティの範囲外アクセス（IndexError）を防ぐ
    if haigou1 >= len(party) or haigou2 >= len(party):
        error("不正なモンスターが選択されました", jump="my_page")

    hai_A = party[haigou1]
    hai_B = party[haigou2]

    # ビジネスルール: 性別（陰陽）チェック
    if hai_A.get("sex") == hai_B.get("sex"):
        error("陰陽が同じで配合出来ません", jump="my_page")

    # ビジネスルール: 配合解禁レベルチェック
    if any(hai.get("lv", 1) < Conf["haigoulevel"] for hai in (hai_A, hai_B)):
        error(
            f"{hai_A['name']}または<br>{hai_B['name']}のレベルが<br>{Conf['haigoulevel']}に達していません",
            jump="my_page",
        )

    # ビジネスルール: 所持金チェック
    cost = (hai_A.get("lv", 1) + hai_B.get("lv", 1)) * 10
    if user.get("money", 0) < cost:
        error("お金が足りません", jump="my_page")

    # 配合ロジックの実行
    new_mons, hint_flag = haigou_sub(hai_A["name"], hai_B["name"])

    # 図鑑登録済みかどうかチェック（未登録なら名前を伏せる）
    if new_mons in zukan and zukan[new_mons].get("get", 0) == 1:
        new_mons_name = new_mons
        hint_flag = False
    else:
        new_mons_name = "？？？"

    # セッションに配合情報を保存（次画面へ引き継ぐため）
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
