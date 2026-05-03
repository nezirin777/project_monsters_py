# name_change.py - ユーザー名変更処理
import os

from sub_def.file_ops import (
    open_user_all,
    save_user_all,
    open_user_list,
    save_user_list,
    open_omiai_list,
)
from sub_def.utils import error, print_html, success
from sub_def.validation import NameChangeForm, validate_form
from sub_def.crypto import set_cookie, get_cookie, verify_password


import conf

Conf = conf.Conf


# ======================#
# 名前変更ページ表示
# ======================#
def name_change(FORM):
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
def name_change_ok(FORM):
    session = FORM.get("s", {})
    user_name = session.get("in_name")
    new_name = FORM.get("new_name", "").strip()
    in_pass = FORM.get("password", "")
    token = session.get("token", "")

    # パスワードも必須項目としてチェック
    if not user_name or not new_name or not in_pass:
        error("必要なパラメータが不足しています。", jump="my_page")

    # ======================
    # 0. セキュリティ: パスワードチェック
    # ======================
    # データ操作前にユーザーデータを読み込み、パスワードを照合する
    all_data = open_user_all(user_name)
    user = all_data.get("user", {})

    if not verify_password(in_pass, user.get("pass", "")):
        error("パスワードが違います", "top")

    # ======================
    # 1. バリデーション
    # ======================
    form = NameChangeForm(data={"new_name": new_name})

    if new_name and new_name == in_pass:
        error("新しい名前とパスワードは違うものにしてください。", jump="my_page")

    validate_form(form, "top")

    if os.path.exists(os.path.join(Conf["savedir"], new_name)):
        error("その名前は既に登録されています。", jump="my_page")

    u_list = open_user_list()
    # 大文字・小文字を区別せずに重複チェック
    if any(u_name.casefold() == new_name.casefold() for u_name in u_list):
        error("その名前では登録することができません。", jump="my_page")

    # ======================
    # 2. 事前準備
    # ======================
    user_list_backup = None

    if user_name in u_list:
        user_list_backup = u_list[user_name].copy()

    old_user_name = user.get("name")  # 元の名前を保持

    # 一時的に名前を変更
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

        # フォルダ名変更後に新しい名前で保存
        save_user_all(all_data, new_name)

    except OSError as e:
        # ROLLBACK処理（OS操作等で失敗した場合、データを元の状態に復元する）
        rollback_success = True
        error_msg = f"フォルダ名変更中にエラーが発生しました: {e}"

        # --- 1. user_list を元に戻す ---
        try:
            if user_list_backup is not None and new_name in u_list:
                u_list[user_name] = u_list.pop(new_name)
                # 元のデータも復元
                u_list[user_name].update(user_list_backup)
                save_user_list(u_list)
        except Exception:
            rollback_success = False

        # --- 2. user_all の名前を元に戻して保存 ---
        try:
            user["name"] = old_user_name
            all_data["user"] = user
            save_user_all(all_data, user_name)  # 古いフォルダに保存
        except Exception:
            rollback_success = False

        if not rollback_success:
            error_msg += "<br>（ロールバック中に一部失敗しました）"

        error(error_msg, jump="top")

    # ======================
    # 5. 成功時のみセッション・クッキー更新
    # ======================
    current_cookie = get_cookie()
    current_cookie["user_name"] = new_name
    set_cookie(current_cookie)

    success(
        f"ユーザー名を{user_name}から{new_name}へ変更しました。",
        jump="top",
    )
