#!D:\Python\Python314\python.exe
# register.py - 新規登録処理

import sys
import cgi
import os
import datetime
import random
import secrets
import shutil
import html
from typing import NoReturn


from sub_def.file_ops import (
    open_user_list,
    save_user_list,
    open_user_all,
    save_user_all,
    open_key_dat,
    open_monster_dat,
    open_tokugi_dat,
    append_log,
)
from sub_def.crypto import (
    hash_password,
    set_cookie,
    set_session,
    get_session,
    token_check,
)
from sub_def.user_ops import get_host, backup
from sub_def.utils import error, print_html
from sub_def.validation import check_valid_user_name_password

import conf

Conf = conf.Conf

# エントリポイントとして UTF-8 出力を強制する
sys.stdout.reconfigure(encoding="utf-8")


def log_registration(in_name: str) -> None:
    """新規登録をBBSログに追加"""
    time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    newlog = (
        f'<div class="bbs-line">'
        f'<span style="color: red; font-weight: bold;">{html.escape(in_name)}</span>さんが参加しました！。 &gt; '
        f'<span class="bbs-time">--{time}</span>'
        f"</div>\n"
    )
    append_log(newlog)


def make_user_all_data(in_name: str, crypted: str, m_name: str) -> dict:
    """user_all.pickle 用の初期データを一括作成"""
    user = {
        "name": in_name,
        "pass": crypted,
        "key": 1,
        "money": 150,
        "medal": 0,
        "isekai_limit": 0,
        "isekai_key": 1,
        "mes": "未登録",
        "getm": "0／0匹(0％)",
    }

    party = [
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
    ]

    room_key = {k: {"no": v["no"], "get": 0} for k, v in open_key_dat().items()}

    Tokugi_dat = open_tokugi_dat()
    waza = {
        name: {"no": v["no"], "type": v["type"], "get": 0}
        for name, v in Tokugi_dat.items()
    }
    waza["通常攻撃"]["get"] = 1

    zukan = {
        k: {"no": v["no"], "m_type": v["m_type"], "get": 0}
        for k, v in open_monster_dat().items()
    }

    vips = {"パーク": 0}
    park = []

    return {
        "user": user,
        "party": party,
        "room_key": room_key,
        "waza": waza,
        "zukan": zukan,
        "vips": vips,
        "park": park,
        "updated_at": datetime.datetime.now().isoformat(),
    }


def create_new_user(in_name: str, crypted: str, m_name: str) -> None:
    """新規ユーザーの user_all.pickle を作成する。失敗時はディレクトリを削除して例外を再送出する"""
    user_dir = os.path.join(Conf["savedir"], in_name)
    pickle_dir = os.path.join(user_dir, "pickle")

    try:
        os.makedirs(pickle_dir, exist_ok=True)
        all_data = make_user_all_data(in_name, crypted, m_name)
        save_user_all(all_data, in_name)
    except Exception as e:
        # 途中まで作成されたディレクトリを確実に削除してから例外を上位に伝播させる
        if os.path.exists(user_dir):
            shutil.rmtree(user_dir, ignore_errors=True)
        raise RuntimeError(f"ユーザー作成に失敗: {e}")


def update_user_list(in_name: str, crypted: str, m_name: str) -> None:
    """ユーザー一覧（グローバル）を更新"""
    try:
        u_list = open_user_list()
        u_list[in_name] = {
            "pass": crypted,
            "host": get_host(),
            "bye": (
                datetime.datetime.now() + datetime.timedelta(days=Conf["goodbye"])
            ).strftime("%Y-%m-%d"),
            "key": 1,
            "m1_name": m_name,
            "m1_hai": 0,
            "m1_lv": 1,
            "m2_name": "",
            "m2_hai": "",
            "m2_lv": "",
            "m3_name": "",
            "m3_hai": "",
            "m3_lv": "",
            "money": 150,
            "mes": "未登録",
            "getm": "0／0匹(0％)",
        }
        save_user_list(u_list)
    except Exception as e:
        raise RuntimeError(f"ユーザー一覧更新に失敗: {e}")


def make_user_data(in_name: str = "", in_pass: str = "", crypted: str = "") -> None:
    """新規ユーザー全データ作成のメイン"""
    crypted = crypted or hash_password(in_pass)

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

    try:
        create_new_user(in_name, crypted, m_name)
        update_user_list(in_name, crypted, m_name)
        log_registration(in_name)
    except Exception:
        # create_new_user / update_user_list が失敗した場合はディレクトリを削除して再送出
        # ※ create_new_user 内でもディレクトリ削除を試みるが、
        #   update_user_list 失敗時のロールバックもここで担保する
        user_dir = os.path.join(Conf["savedir"], in_name)
        shutil.rmtree(user_dir, ignore_errors=True)
        raise


def sinki(FORM: dict, kanri: bool = False) -> NoReturn:
    """
    新規登録処理の本体。
    全コードパスが error() または print_html() で終わる（どちらも NoReturn）。
    """
    form = check_valid_user_name_password(FORM)
    in_name = form.new_user_name.data
    in_pass = form.new_password.data

    user_dir = os.path.join(Conf["savedir"], in_name)
    if os.path.exists(user_dir):
        error("その名前は既に登録されています", "top")

    u_list = open_user_list()
    lower_names = {u.casefold() for u in u_list}
    if in_name.casefold() in lower_names:
        error("その名前は使用できません", "top")

    if Conf["iplog"] == 1 and not kanri:
        host = get_host()
        if any(u["host"] == host for u in u_list.values()):
            error("重複登録の可能性があります。現在の設定では参加出来ません。", "top")

    make_user_data(in_name, in_pass)
    backup()

    set_cookie({"in_name": in_name, "last_floor": 1, "last_room": ""})

    all_data = open_user_all(in_name)
    party = all_data["party"]

    k_txt = "管理モードで登録しました" if kanri else "登録が完了しました"

    context = {
        "Conf": Conf,
        "k_txt": k_txt,
        "in_name": in_name,
        "in_pass": in_pass,
        "money": 150,
        "key_floor": "地下1階",
        "monster": party[0],
        "kanri": kanri,
    }
    # 完了画面のテンプレートを呼び出し（NoReturn）
    print_html("newgame_result_tmp.html", context)


# ====================================================================================#
def main() -> None:
    if os.path.exists("mente.mente"):
        error(
            "現在メンテナンスモードに入ってます。<br>終了までお待ちくださいませ。",
            "top",
        )

    form = cgi.FieldStorage()

    FORM = {key: form.getfirst(key) for key in form}

    if len(open_user_list()) >= Conf["sankaMAX"]:
        error("参加人数上限を超えています。申し訳ありません。", "top")

    if "mode" not in FORM:
        new_session = {"token": secrets.token_hex(16)}
        set_session(new_session)
        print_html("newgame_tmp.html", {"token": new_session["token"], "Conf": Conf})

    elif FORM["mode"] == "sinki":
        FORM["s"] = token_check(FORM, get_session())
        sinki(FORM)

    else:
        # 未知の mode は不正アクセスとみなしてトップへ戻す
        error(f"無効なモードです: {FORM.get('mode')}", "top")


# ====================================================================================#

if __name__ == "__main__":
    main()
    # main() は内部で print_html / error / sinki のいずれかを経由して sys.exit() するが、
    # 万が一の素通り（予期しない return）に備えた安全網として明示的に終了する
    sys.exit()
