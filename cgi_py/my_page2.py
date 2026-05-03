# my_page2.py - 他ユーザー閲覧用


def my_page2(FORM):
    """他ユーザーのマイページ表示（閲覧専用・簡易版）"""
    from sub_def.utils import print_html, error
    from sub_def.file_ops import open_user_all
    from sub_def.utils import slim_number_with_cookie
    import conf

    Conf = conf.Conf

    user_name = FORM.get("target_user")
    fol = FORM.get("fol", "")

    if not user_name:
        error("ユーザー名が指定されていません。", jump="top")

    # user_all で一括取得
    all_data = open_user_all(user_name)
    user = all_data["user"]
    party = all_data["party"]
    vips = all_data.get("vips", {})  # 将来的に使用する可能性があるため取得

    user_v = slim_number_with_cookie(user)

    # 追加情報生成
    isekai = "hidden" if not user.get("isekai_limit") else ""

    # 表示用データ準備
    option_list = list(range(1, len(party) + 1))
    party_with_index = list(enumerate(slim_number_with_cookie(party), 1))

    # テンプレートに渡す内容
    content = {
        "Conf": Conf,
        "user_name": user_name,
        "token": "",  # 閲覧専用なので空でOK
        "isekai": isekai,
        "user": user,
        "user_v": user_v,
        "party_with_index": party_with_index,
        "option_list": option_list,
        "fol": fol,
        "my_page_flg": 0,  # 重要：編集機能などを非表示にするフラグ
    }

    print_html("my_page_tmp.html", content)
