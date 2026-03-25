import html
import re
from sub_def.utils import error, print_html
from sub_def.file_ops import open_user, save_user, open_user_list, save_user_list

import conf

Conf = conf.Conf


def validate_input(in_name, mes):
    """入力検証: 名前とメッセージのバリデーション"""
    if not in_name or not in_name.strip():
        error("名前を入力してください。")
    if not (2 <= len(mes) <= 50):
        error("メッセージは2文字以上、50文字以下で入力してください。")


def sanitize_message(mes):
    """メッセージのフィルタリングとエスケープ処理"""
    mes = re.sub(r"[\r\n]", " ", mes)  # 改行コードをスペースに置換
    mes = html.escape(mes)
    return mes


def comment(FORM):
    in_name = FORM.get("username")
    mes = FORM.get("message", "")
    token = FORM("token")

    # 入力検証
    validate_input(in_name, mes)

    # ユーザーリストとユーザーデータの取得
    u_list = open_user_list()
    user = open_user()

    # 名前の存在確認
    if in_name not in u_list:
        error("指定された名前のユーザーは存在しません。")

    # メッセージの保存
    safe_mes = sanitize_message(mes)
    u_list[in_name]["mes"] = safe_mes
    user["mes"] = safe_mes

    save_user_list(u_list)
    save_user(user)

    content = {
        "Conf": Conf,
        "token": token,
        "mes": "メッセージは更新されました",
    }

    print_html("result_tmp.html", content)
