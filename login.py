#!D:\Python\Python312\python.exe

import sys
import cgi
import os
import secrets

import sub_def
import conf
import cgi_py

Conf = conf.Conf

sys.stdout.reconfigure(encoding="utf-8")


# 自動でutf-8にエンコードされて出力される

# フォームの関数マッピング
FUNCTION_MAP = {
    # my_page画面 #
    "my_page": cgi_py.my_page.my_page,
    "my_page2": cgi_py.my_page2.my_page2,
    "change": cgi_py.change.change,
    # 	コメント更新  #
    "comment": cgi_py.comment.comment,
    # 	魔物図鑑    #
    "zukan": cgi_py.zukan.zukan,
    # 	本屋さん  #
    "books": cgi_py.books.books,
    "book_read": cgi_py.books.book_read,
    # 宿屋開始 #
    "yadoya": cgi_py.yadoya.yadoya,
    "yadoya_ok": cgi_py.yadoya.yadoya_ok,
    # 教会     #
    "kyoukai": cgi_py.kyoukai.kyoukai,
    "kyoukai_ok": cgi_py.kyoukai.kyoukai_ok,
    # メダル交換所 #
    "medal_shop": cgi_py.shop_base.medal_shop,
    "medal_shop_ok": cgi_py.medal_shop.medal_shop_ok,
    # ユーザー名変更 #
    "name_change": cgi_py.name_change.name_change,
    "name_change_check": cgi_py.name_change.name_change_check,
    "name_change_ok": cgi_py.name_change.name_change_ok,
    # 性転換所  #
    "seitenkan": cgi_py.seitenkan.seitenkan,
    "seitenkan_ok": cgi_py.seitenkan.seitenkan_ok,
    # モンスターパーク	#
    "park": cgi_py.park.park,
    "park_1": cgi_py.park.park_1,
    "park_2": cgi_py.park.park_2,
    # 	VIPS関連処理  #
    "v_shop": cgi_py.shop_base.v_shop,
    "v_shop_ok": cgi_py.v_shop.v_shop_ok,
    "v_shop2": cgi_py.shop_base.v_shop2,
    "v_shop2_ok": cgi_py.v_shop2.v_shop2_ok,
    # 	配合  #
    "haigou_check": cgi_py.haigou_check.haigou_check,
    "haigou_hensin": cgi_py.haigou_hensin.haigou_hensin,
    #  戦闘  #
    "battle_type": cgi_py.battle_type.battle_type,
    "battle_type2": cgi_py.battle_type.battle_type2,
    "battle_fight": cgi_py.battle_fight.battle_fight,
    #  モンスタゲット   #
    "m_get": cgi_py.m_get.m_get,
    "m_bye": cgi_py.m_bye.m_bye,
    #  部屋鍵get  #
    "roomkey_get": cgi_py.roomkey_get.roomkey_get,
    # 	メダル獲得杯   #
    "tournament_result": cgi_py.tournament_result.tournament_result,
    # 	お見合い関係  #
    "omiai_room": cgi_py.omiai_room.omiai_room,
    "omiai_touroku": cgi_py.omiai_touroku.omiai_touroku,
    "omiai_touroku_cancel": cgi_py.omiai_touroku.omiai_touroku_cancel,
    "omiai_request": cgi_py.omiai_request.omiai_request,
    "omiai_request_ok": cgi_py.omiai_request.omiai_request_ok,
    "omiai_request_cancel": cgi_py.omiai_request.omiai_request_cancel,
    "omiai_answer_no": cgi_py.omiai_answer.omiai_answer_no,
    "omiai_answer_ok": cgi_py.omiai_answer.omiai_answer_ok,
    "omiai_answer_result": cgi_py.omiai_answer.omiai_answer_result,
    "omiai_baby_get": cgi_py.omiai_baby.omiai_baby_get,
    # 	数値表記法    #
    "number_unit": cgi_py.number_unit.number_unit,
}


# ====================================================================================#


def token_check(form):
    """トークンの一致を確認し、新しいトークンを生成してセッションに保存"""
    session = sub_def.get_session()
    form["s"] = session

    token = form.get("token")
    if not token or not secrets.compare_digest(session["token"], token):
        # sub_def.error("トークンが一致しないです", "top")
        pass

    new_token = secrets.token_hex(16)
    session_data = {
        "token": new_token,
        "name": form.get("name", session.get("name", "")),
        "password": form.get("password", session.get("password", "")),
    }
    sub_def.set_session(session_data)
    return session_data


def reg_check(form):
    """ユーザー登録とパスワードの一致を確認"""
    name = form.get("name")
    password = form.get("password")

    if not name:
        sub_def.error("名前がありません", "top")

    if not password:
        sub_def.error("パスワードがありません", "top")

    user_path = os.path.join(Conf["savedir"], name)
    if not os.path.exists(user_path):
        sub_def.error("あなたは未登録のようです。", "top")

    user = sub_def.open_user(name)
    if user["pass"] == sub_def.pass_encode(password):
        # 新しいSHA256ハッシュを保存
        user["pass"] = sub_def.hash_password(password)
        sub_def.save_user(user, name)

    if sub_def.verify_password(password, user["pass"]) == False:
        sub_def.error("パスワードが違います", "top")

    cookie = sub_def.get_cookie()
    cookie.update({"in_name": name, "in_pass": password})
    sub_def.set_cookie(cookie)
    return cookie


def dispatch_function(form):
    """フォームのモードに基づき対応する関数を呼び出す"""
    mode = form.get("mode")
    func = FUNCTION_MAP.get(mode)
    if func:
        func(form)
    else:
        raise ValueError(f"[{mode}]が実行できませんでした。")


def is_maintenance_mode():
    return os.path.exists("mente.mente")


def main():
    if is_maintenance_mode():
        raise RuntimeError(
            "現在メンテナンス中です。しばらくしてから再度アクセスしてください。"
        )

    # フォームを辞書化
    form = cgi.FieldStorage()
    FORM = {key: form.getvalue(key) for key in form.keys()}

    # GETメソッドとモードによる条件分岐と処理
    if os.environ["REQUEST_METHOD"] != "POST":
        if FORM.get("mode") in ("tournament_result", "my_page2", "zukan"):
            dispatch_function(FORM)
            sys.exit()
        else:
            sub_def.error(f"モード選択がおかしいです？[{FORM.get('mode','空っぽ')}]")

    # 認証とトークンチェック
    FORM.update(token_check(FORM))
    FORM["c"] = reg_check(FORM)

    # 指定されたモードの関数を呼び出し
    dispatch_function(FORM)

    # 出力
    sub_def.result(print("あっれれ～？おっかしぃぞ～？"))


# ====================================================================================#

if __name__ == "__main__":
    main()
