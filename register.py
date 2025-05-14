#!D:\Python\Python312\python.exe

import sys
import cgi
import os
import datetime
import random
import secrets
import shutil
import unicodedata
import re
import emoji

import sub_def
import conf

Conf = conf.Conf
sys.stdout.reconfigure(encoding="utf-8")
# 自動でutf-8にエンコードされて出力される


def update_logfile(in_name):
    """新規登録ユーザーをBBSログに追加"""
    logfile = os.path.join(".", Conf["savedir"], "bbslog.log")
    time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    newlog = f"""<hr><font color="red">{in_name}</font>さんが参加しました！。 <font size="1">--{time}</font>\n"""

    os.makedirs(os.path.dirname(logfile), exist_ok=True)

    with open(logfile, mode="r+", encoding="utf-8_sig") as f:
        log = f.readlines()
        log.insert(0, newlog)
        log = log[:50]  # 最新50行に制限
        f.seek(0)
        f.truncate()
        f.writelines(log)


def make_user_data(in_name="", in_pass="", crypted=""):
    # cryptedは管理モード/リスタート用

    user_dir = os.path.join(Conf["savedir"], in_name)
    created_files = []

    try:
        os.makedirs(f"{user_dir}/pickle", exist_ok=True)
        created_files.append(user_dir)
        crypted = crypted or sub_def.hash_password(in_pass)

        monset = [
            "スライム",
            "ドラゴンキッズ",
            "ベロゴン",
            "ピッキー",
            "マッドプラント",
            "キリキリバッタ",
            "ピクシー",
            "ゴースト",
            "トーテムキラー",
        ]
        m_name = random.choice(monset)

        # ユーザーデータ
        sub_def.save_user(
            {
                "name": in_name,
                "pass": crypted,
                "key": 1,
                "money": 100,
                "medal": 0,
                "isekai_limit": 0,
                "isekai_key": 1,
                "mes": "未登録",
                "getm": "0／0匹(0％)",
            },
            in_name,
        )

        # パーティーデータ
        sub_def.save_party(
            [
                {
                    "no": 1,
                    "name": m_name,
                    "lv": 1,
                    "mlv": 10,
                    "hai": 0,
                    "hp": 5,
                    "mhp": 5,
                    "mp": 5,
                    "mmp": 5,
                    "atk": 5,
                    "def": 5,
                    "agi": 5,
                    "exp": 0,
                    "n_exp": 10,
                    "sei": "ふつう",
                    "sex": random.choice(Conf["sex"]),
                }
            ],
            in_name,
        )

        # 追加データの初期化
        sub_def.save_room_key(
            {k: {"no": v["no"], "get": 0} for k, v in sub_def.open_key_dat().items()},
            in_name,
        )

        Tokugi_dat = sub_def.open_tokugi_dat()
        waza = {
            name: {"no": v["no"], "type": v["type"], "get": 0}
            for name, v in Tokugi_dat.items()
        }
        waza["通常攻撃"]["get"] = 1
        sub_def.save_waza(waza, in_name)

        sub_def.save_zukan(
            {
                k: {"no": v["no"], "m_type": v["m_type"], "get": 0}
                for k, v in sub_def.open_monster_dat().items()
            },
            in_name,
        )
        sub_def.save_vips({"パーク": 0}, in_name)
        sub_def.save_park([], in_name)

        # ユーザー一覧の更新
        u_list = sub_def.open_user_list()
        u_list[in_name] = {
            "pass": crypted,
            "host": sub_def.get_host(),
            "bye": (
                datetime.datetime.now() + datetime.timedelta(days=Conf["goodbye"])
            ).strftime("%Y-%m-%d"),
            "key": 1,
            "m1_name": m_name,
            "m1_hai": 0,
            "m1_lv": 5,
            "m2_name": "",
            "m2_hai": "",
            "m2_lv": "",
            "m3_name": "",
            "m3_hai": "",
            "m3_lv": "",
            "money": 50,
            "mes": "未登録",
            "getm": 0,
        }
        sub_def.save_user_list(u_list)

        update_logfile(in_name)

    except Exception as e:
        # エラー発生時のクリーンアップ
        if os.path.exists(user_dir):
            shutil.rmtree(user_dir)
        sub_def.error(f"データ作成中にエラーが発生しました: {e}", "top")


def sinki(FORM, kanri=False):
    # 引数は管理画面からの強制登録用
    """新規ユーザー登録のメイン処理"""
    in_name = unicodedata.normalize("NFKC", FORM.get("new_username", ""))
    in_pass = FORM.get("new_password")

    sub_def.check_valid_username_password(FORM)

    user_dir = os.path.join(Conf["savedir"], in_name)
    if os.path.exists(user_dir):
        return sub_def.error("その名前は既に登録されています", "top")

    u_list = sub_def.open_user_list()

    # 大文字・小文字を無視した重複名チェック
    if in_name.casefold() in (u.casefold() for u in u_list):
        return sub_def.error("その名前では登録することができません。", "top")

    if Conf["iplog"] == 1 and not kanri:  # 管理モードの強制登録では重複判定スルー
        host = sub_def.get_host()
        if any(u["host"] == host for u in u_list.values()):
            return sub_def.error(
                "重複登録の可能性があります。現在の設定では参加出来ません。", "top"
            )

    make_user_data(in_name, in_pass)
    sub_def.backup()

    sub_def.set_cookie(
        {"in_name": in_name, "in_pass": in_pass, "last_floor": 1, "last_room": ""}
    )

    party = sub_def.open_party(in_name)

    k_txt = (
        "管理モードで強制登録しました。"
        if kanri
        else "以下の内容で登録が完了しました。"
    )

    # テンプレートに渡すデータ
    context = {
        "k_txt": k_txt,
        "in_name": in_name,
        "in_pass": in_pass,
        "money": 50,
        "key_floor": "地下1階",
        "monster": party[0],
        "Conf": Conf,
        "kanri": kanri,
    }
    sub_def.print_html("newgame_result_tmp.html", context)


# ====================================================================================#
def token_check(FORM):
    """トークン検証・新規生成"""
    session = sub_def.get_session()
    form_token = FORM.get("token", "")
    session_token = session.get("token", "")

    if not form_token or not secrets.compare_digest(session_token, form_token):
        sub_def.error("トークンが一致しないです。", "top")

    session["token"] = secrets.token_hex(16)
    sub_def.set_session(session)
    return session


def main():
    if os.path.exists("mente.mente"):
        return sub_def.error(
            "現在メンテナンスモードに入ってます。<br>終了までお待ちくださいませ。",
            "top",
        )

    form = cgi.FieldStorage()
    FORM = {key: form.getvalue(key) for key in form.keys()}

    if len(sub_def.open_user_list()) >= Conf["sankaMAX"]:
        return sub_def.error("参加人数上限を超えています。申し訳ありません。", "top")

    if "mode" not in FORM:
        FORM["token"] = secrets.token_hex(16)
        sub_def.set_session(FORM)
        sub_def.print_html("newgame_tmp.html", {"token": FORM["token"]})

    elif FORM["mode"] == "sinki":
        token_check(FORM)
        sinki(FORM)


# ====================================================================================#

if __name__ == "__main__":
    main()
    sys.exit()
