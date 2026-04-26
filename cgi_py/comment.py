import html
import re

from sub_def.utils import error, success
from sub_def.file_ops import (
    open_user_all,
    save_user_all,
    open_user_list,
    save_user_list,
)

import conf

Conf = conf.Conf


def validate_input(user_name, mes):
    """入力検証: 名前とメッセージのバリデーション"""
    if not user_name or not user_name.strip():
        error("名前を入力してください。")
    if not (2 <= len(mes) <= 50):
        error("メッセージは2文字以上、50文字以下で入力してください。")


def sanitize_message(mes):
    """メッセージのフィルタリングとエスケープ処理"""
    mes = re.sub(r"[\r\n]", " ", mes)  # 改行コードをスペースに置換
    mes = html.escape(mes)
    return mes


def comment(FORM):
    """メッセージ（自己紹介文）更新処理（user_all対応版）"""
    user_name = FORM["s"].get("in_name")
    mes = FORM.get("message", "")

    # 入力検証
    validate_input(user_name, mes)

    # 新形式でユーザー全データを取得
    all_data = open_user_all(user_name)
    user = all_data.get("user", {})

    # ユーザーリスト取得
    u_list = open_user_list()

    # 名前の存在確認
    if user_name not in u_list:
        error("指定された名前のユーザーは存在しません。")

    # メッセージのサニタイズと更新
    safe_mes = sanitize_message(mes)

    # user_all内のuserデータ更新
    user["mes"] = safe_mes

    # ユーザーリスト側のmesも更新（表示用）
    if user_name in u_list:
        u_list[user_name]["mes"] = safe_mes

    # 保存処理（user_all と user_list の両方を更新）
    all_data["user"] = user
    save_user_all(all_data, user_name)
    save_user_list(u_list)

    success("メッセージが更新されました。", "my_page")
