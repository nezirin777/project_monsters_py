# roomkey_get.py -部屋の鍵を入手する

from sub_def.file_ops import open_user_all, save_user_all
from sub_def.utils import error, success


def roomkey_get(FORM):
    # セッション切れ等による KeyError を防ぐための安全な取得
    session = FORM.get("s", {})
    user_name = session.get("in_name")
    get_key = FORM.get("get_key")

    if not user_name:
        error("セッション情報が不正です。", jump="top")

    # get_keyが指定されていない場合のエラーハンドリング
    if not get_key:
        error("エラーが発生しました。<br>roomkey_get", jump="my_page")

    # room_keyのデータを取得
    user_all = open_user_all(user_name)
    room_key = user_all.get("room_key", {})

    # get_keyがroom_keyに存在するかチェック
    if get_key not in room_key:
        # 以前はエラーで弾いていましたが、アップデートで新種の鍵が追加された場合など、
        # 古いユーザーデータに枠が存在しなくて進行不能になるのを防ぐため、自動で枠を作成します。
        room_key[get_key] = {}

    # 該当するキーの "get" フラグを更新 (1 = 入手済み)
    room_key[get_key]["get"] = 1

    # user_allに反映して保存
    user_all["room_key"] = room_key
    save_user_all(user_all, user_name)

    # 結果を出力
    success(f"{get_key}の部屋の鍵を入手した！", jump="my_page")
