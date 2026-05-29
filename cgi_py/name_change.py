# name_change.py - ユーザー名変更処理

import os
from typing import NoReturn

from sub_def.file_ops import (
    open_user_all,
    save_user_all,
    open_user_list,
    save_user_list,
    open_omiai_list,
)
from sub_def.utils import error, print_html, success
from sub_def.validation import name_change_check
from sub_def.crypto import set_cookie, get_cookie, verify_password

import conf

Conf = conf.Conf


# ======================#
# 名前変更ページ表示
# ======================#
def name_change(FORM: dict) -> NoReturn:
    """名前変更フォーム表示"""
    session = FORM.get("s", {})
    user_name = session.get("in_name")
    token = session.get("token", "")

    if not user_name:
        error("ユーザー名が取得できませんでした。", jump="my_page")

    if open_omiai_list().get(user_name):
        error("お見合い所を使用中はユーザー名の変更ができません。", jump="my_page")

    content = {
        "Conf": Conf,
        "current_name": user_name,
        "token": token,
    }

    print_html("name_change_tmp.html", content)


# ======================#
# 名前変更実行
# ======================#
def name_change_ok(FORM: dict) -> NoReturn:
    """
    ユーザー名変更の実行処理。
    パスワード照合 → バリデーション → user_list 更新 → フォルダ名変更 の順に処理し、
    フォルダ名変更失敗時はロールバックを試みる。
    """
    session = FORM.get("s", {})
    user_name = session.get("in_name")
    in_pass = FORM.get("password", "")

    if not user_name or not FORM.get("new_name", "").strip() or not in_pass:
        error("必要なパラメータが不足しています。", jump="my_page")

    # ======================
    # 0. セキュリティ: パスワードチェック
    # ======================
    # バリデーション前にパスワードを照合し、不正操作を早期遮断する
    all_data = open_user_all(user_name)
    user = all_data.get("user", {})

    if not verify_password(in_pass, user.get("pass", "")):
        error("パスワードが違います", "top")

    # ======================
    # 1. バリデーション
    # ======================
    # name_change_check が NFKC 正規化・フォーマット検証・名前=パスワード一致チェックを行う
    form = name_change_check(FORM)
    new_name = form.new_name.data  # 正規化済みの値を以降で使用

    if os.path.exists(os.path.join(Conf["savedir"], new_name)):
        error("その名前は既に登録されています。", jump="my_page")

    u_list = open_user_list()
    if any(u_name.casefold() == new_name.casefold() for u_name in u_list):
        error("その名前では登録することができません。", jump="my_page")

    # ======================
    # 2. 事前準備
    # ======================
    user_list_backup = u_list[user_name].copy() if user_name in u_list else None
    old_user_name = user.get("name")

    user["name"] = new_name
    all_data["user"] = user

    # ======================
    # 3. グローバルユーザー一覧の更新
    # ======================
    try:
        if user_name in u_list:
            u_list[new_name] = u_list.pop(user_name)
            save_user_list(u_list)
    except Exception as e:
        error(f"user_list更新中にエラーが発生しました: {e}", jump="top")

    # ======================
    # 4. フォルダ名変更（最も危険な処理とロールバック機構）
    # ======================
    old_path = os.path.join(Conf["savedir"], user_name)
    new_path = os.path.join(Conf["savedir"], new_name)

    try:
        if os.path.exists(old_path):
            os.rename(old_path, new_path)

        save_user_all(all_data, new_name)

    except OSError as e:
        rollback_success = True
        error_msg = f"フォルダ名変更中にエラーが発生しました: {e}"

        try:
            if user_list_backup is not None and new_name in u_list:
                u_list[user_name] = u_list.pop(new_name)
                u_list[user_name].update(user_list_backup)
                save_user_list(u_list)
        except Exception:
            rollback_success = False

        try:
            user["name"] = old_user_name
            all_data["user"] = user
            save_user_all(all_data, user_name)
        except Exception:
            rollback_success = False

        if not rollback_success:
            error_msg += "<br>（ロールバック中に一部失敗しました）"

        error(error_msg, jump="top")

    # ======================
    # 5. 成功時のみセッション・クッキー更新
    # ======================
    # 永続クッキーのユーザー名を新しい名前に更新する。
    # キーは他のファイル（register.py, validation.py 等）と統一して "in_name" を使用する。
    current_cookie = get_cookie()
    current_cookie["in_name"] = new_name
    set_cookie(current_cookie)

    success(
        f"ユーザー名を{user_name}から{new_name}へ変更しました。",
        jump="top",
    )
