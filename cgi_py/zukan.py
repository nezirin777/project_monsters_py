# zukan.py - 図鑑ページ処理

from sub_def.file_ops import open_user_all, open_monster_dat
from sub_def.utils import print_html, error
from sub_def.crypto import get_cookie, get_session

import conf

Conf = conf.Conf


def zukan(FORM: dict) -> None:
    """
    指定ユーザーの魔物図鑑を表示する。

    マスターデータを土台にしてユーザーの取得状況を上書き結合することで、
    未取得モンスターの空枠も含めて表示できる設計になっている。
    本人アクセス時（ref=True）のみツールチップ（配合レシピ）を表示する。
    """
    user_name = FORM.get("user_name")

    if not user_name:
        error("ユーザー名が指定されていません。", jump="top")

    m_type = FORM.get("type", "スライム系")
    fol = FORM.get("fol", "")

    session = get_session()

    user_all = open_user_all(user_name)

    # URL直叩き等で存在しないユーザー名が指定された場合のエラーハンドリング
    if not user_all:
        error("指定されたユーザーのデータが見つかりません。", jump="top")

    user = user_all.get("user", {})
    # 変数名の衝突を避けるため user_zukan という名前を使用する
    # （関数名 zukan と同名の変数にすると同スコープ内で混乱を招く）
    user_zukan = user_all.get("zukan", {})

    M_list = open_monster_dat()

    # マスターデータから重複なくカテゴリ一覧を生成（dict.fromkeys で順序を保持）
    categories = list(
        dict.fromkeys(
            info.get("m_type") for info in M_list.values() if info.get("m_type")
        )
    )

    cookie = get_cookie()
    # ログイン中のユーザー名と表示対象のユーザー名が一致すれば本人アクセスと判定する
    ref = cookie.get("in_name", "") == user_name

    # マスターデータを土台にしてユーザーの取得状況を上書き結合する。
    # {**m_data, **user_zu} で結合し、ユーザー側（取得フラグ等）がマスター側を上書きする。
    # ユーザーデータに存在しないモンスターでも m_data が土台になるため空枠が表示される。
    filtered_zukan: dict = {}
    for name, m_data in M_list.items():
        if m_type != m_data.get("m_type"):
            continue

        user_zu = user_zukan.get(name, {})
        merged_data = {**m_data, **user_zu}

        # 1. ツールチップ用のレシピ配列を作成（血統1〜3を探索）
        recipes = []
        for i in range(1, 4):
            kettou = m_data.get(f"血統{i}")
            aite = m_data.get(f"相手{i}")
            if kettou and aite:
                recipes.append(f"{kettou} × {aite}")
        merged_data["recipes"] = recipes

        # 2. 表示名と CSS クラスの確定（未取得は名前・背景を伏せる）
        is_get = merged_data.get("get", 0) == 1
        merged_data["display_name"] = name if is_get else "？？？"
        merged_data["display_class"] = merged_data.get("m_type", "") if is_get else ""

        # 3. ツールチップ表示フラグの確定
        # 本人アクセス かつ 取得済み かつ レシピが存在する場合のみ True
        merged_data["show_tooltip"] = bool(ref and is_get and recipes)

        filtered_zukan[name] = merged_data

    # 図鑑ナンバー（no）の数値順にソート
    zukan_list = dict(
        sorted(filtered_zukan.items(), key=lambda item: int(item[1].get("no", 0)))
    )

    content = {
        "Conf": Conf,
        "user_name": user_name,
        "user": user,
        "zukan_list": zukan_list,
        "m_type": m_type,
        "categories": categories,
        "ref": ref,
        "fol": fol,
        "token": session.get("token", ""),
    }

    print_html("zukan_tmp.html", content)
