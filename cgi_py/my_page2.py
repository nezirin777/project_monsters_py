# my_page2.py - 他ユーザー閲覧用

from typing import NoReturn

from sub_def.utils import error, print_html, slim_number_with_cookie
from sub_def.file_ops import open_user_all

import conf

Conf = conf.Conf


def my_page2(FORM: dict) -> NoReturn:
    """他ユーザーのマイページ表示（閲覧専用・簡易版）"""
    user_name = FORM.get("target_user")
    fol = FORM.get("fol", "")

    if not user_name:
        error("ユーザー名が指定されていません。", jump="top")

    # user_all で一括取得
    all_data = open_user_all(user_name)
    user = all_data.get("user", {})
    party = all_data.get("party", [])
    vips = all_data.get("vips", {})  # 将来的に使用する可能性があるため取得

    user_v = slim_number_with_cookie(user)

    # 古いデータでは空文字が入る場合があるため `or 0` で安全に数値化する（my_page.py と統一）
    isekai_limit = int(user.get("isekai_limit") or 0)
    # 異世界機能が未解放の場合は UI を非表示にする（isekai="hidden"）
    isekai = "hidden" if not isekai_limit else ""

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
        # my_page_tmp.html が {% if my_page_flg %} の外で boost_flg を参照するため明示する。
        # 他人のページを閲覧する際はブースト状態を表示しない。
        "boost_flg": False,
        "boost_time": "",
    }

    print_html("my_page_tmp.html", content)
