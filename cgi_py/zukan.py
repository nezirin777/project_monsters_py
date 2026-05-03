# zukan.py - 図鑑ページ処理

from sub_def.file_ops import open_user_all, open_monster_dat
from sub_def.utils import print_html, error
from sub_def.crypto import get_cookie

import conf

Conf = conf.Conf


def zukan(FORM):
    user_name = FORM.get("user_name")

    if not user_name:
        error("ユーザー名が指定されていません。", jump="top")

    m_type = FORM.get("type", "スライム系")
    fol = FORM.get("fol", "")

    user_all = open_user_all(user_name)

    # 万が一、URL直叩き等で存在しない他人の名前が指定された場合のエラーハンドリング
    if not user_all:
        error("指定されたユーザーのデータが見つかりません。", jump="top")

    user = user_all.get("user", {})
    zukan = user_all.get("zukan", {})

    M_list = open_monster_dat()

    # マスターデータからカテゴリ一覧を生成
    categories = list(
        dict.fromkeys(
            info.get("m_type") for info in M_list.values() if info.get("m_type")
        )
    )

    ccc = get_cookie()
    ref = ccc.get("in_name", "") == user_name

    # ループの土台を「ユーザーデータ」から「マスターデータ」に変更
    filtered_zukan = {}
    for name, m_data in M_list.items():
        if m_type == m_data.get("m_type"):
            # マスターのデータ(枠)に対して、ユーザーの取得状況(get=1など)を上書き結合
            # {**A, **B} で辞書を結合。B(ユーザーの取得フラグ等)でA(マスター)を上書きする
            # ユーザーデータに存在しないモンスターでも m_data が土台になるため空枠が表示される
            user_zu = zukan.get(name, {})
            merged_data = {**m_data, **user_zu}
            recipes = []
            for i in range(1, 4):  # 血統1〜3までを探索
                kettou = m_data.get(f"血統{i}")
                aite = m_data.get(f"相手{i}")
                if kettou and aite:
                    recipes.append(f"{kettou} × {aite}")
            merged_data["recipes"] = recipes

            filtered_zukan[name] = merged_data

    filtered_zukan = {}
    for name, m_data in M_list.items():
        if m_type == m_data.get("m_type"):
            # マスターのデータ(枠)に対して、ユーザーの取得状況(get=1など)を上書き結合
            # {**A, **B} で辞書を結合。B(ユーザーの取得フラグ等)でA(マスター)を上書きする
            user_zu = zukan.get(name, {})
            merged_data = {**m_data, **user_zu}

            # 1. ツールチップ用のレシピ配列作成
            recipes = []
            for i in range(1, 4):
                kettou = m_data.get(f"血統{i}")
                aite = m_data.get(f"相手{i}")
                if kettou and aite:
                    recipes.append(f"{kettou} × {aite}")
            merged_data["recipes"] = recipes

            # 2.表示名とCSSクラスの確定
            is_get = merged_data.get("get", 0) == 1
            merged_data["display_name"] = name if is_get else "？？？"
            merged_data["display_class"] = (
                merged_data.get("m_type", "") if is_get else ""
            )

            # ★3. ツールチップを表示するべきかどうかの「判定フラグ」を確定！
            # （本人アクセス ＆ 取得済み ＆ レシピが存在する 場合のみ True）
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
        "token": FORM.get("s", {}).get("token", ""),
    }

    print_html("zukan_tmp.html", content)
