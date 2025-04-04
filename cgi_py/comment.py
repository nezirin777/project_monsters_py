import urllib.parse
import re
import sub_def


def validate_input(in_name, mes):
    """入力検証: 名前とメッセージのバリデーション"""
    if not in_name:
        sub_def.error("名前を入力してください。")
    if not (2 <= len(mes) <= 50):
        sub_def.error("メッセージは2文字以上、50文字以下で入力してください。")


def sanitize_message(mes):
    """メッセージのフィルタリングとエスケープ処理"""
    mes = urllib.parse.unquote(mes)  # URLデコード
    mes = re.sub(r"[<>]", "-", mes)  # 特殊文字の置換
    mes = re.sub(r"[\r\n]", " ", mes)  # 改行コードをスペースに置換
    return mes


def comment(FORM):
    in_name = FORM.get("name")
    mes = FORM.get("message", "")

    # 入力検証
    validate_input(in_name, mes)

    # ユーザーリストとユーザーデータの取得
    u_list = sub_def.open_user_list()
    user = sub_def.open_user()

    # 名前の存在確認
    if in_name not in u_list:
        sub_def.error("指定された名前のユーザーは存在しません。")

    # メッセージの保存
    u_list[in_name]["mes"] = sanitize_message(mes)
    user["mes"] = sanitize_message(mes)

    sub_def.save_user_list(u_list)
    sub_def.save_user(user)

    sub_def.result("メッセージは更新されました", "", FORM["token"])
