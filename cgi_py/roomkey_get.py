# roomkey_get.py - 部屋の鍵を入手する

from typing import NoReturn

from sub_def.file_ops import open_user_all, save_user_all
from sub_def.utils import error, success


def roomkey_get(FORM: dict) -> NoReturn:
    """
    戦闘勝利後の部屋の鍵取得処理。
    鍵の枠がユーザーデータに存在しない場合（アップデートで追加された新種の鍵等）は
    自動で枠を作成して進行不能を防ぐ。
    """
    # セッション切れ等による KeyError を防ぐための安全な取得
    session = FORM.get("s", {})
    user_name = session.get("in_name")
    get_key = FORM.get("get_key")

    if not user_name:
        error("セッション情報が不正です。", jump="top")

    # get_key が指定されていない場合のエラーハンドリング
    if not get_key:
        error("エラーが発生しました。<br>roomkey_get", jump="my_page")

    # room_key のデータを取得
    user_all = open_user_all(user_name)
    room_key = user_all.get("room_key", {})

    # get_key が room_key に存在するかチェック。
    # 存在しない場合は自動で枠を作成する（アップデートで新種の鍵が追加されたとき等、
    # 古いユーザーデータに枠がなくて進行不能になるのを防ぐため）。
    if get_key not in room_key:
        room_key[get_key] = {}

    # 該当するキーの "get" フラグを更新 (1 = 入手済み)
    room_key[get_key]["get"] = 1

    # user_all に反映して保存
    user_all["room_key"] = room_key
    save_user_all(user_all, user_name)

    success(f"{get_key}の部屋の鍵を入手した！", jump="my_page")
