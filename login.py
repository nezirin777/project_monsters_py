#!D:\Python\Python314\python.exe

# login.py - ログイン処理とエラーハンドリング

import sys
import cgi
import os
import importlib
import traceback
import types
from typing import NoReturn

import conf

from sub_def.crypto import get_session, token_check
from sub_def.utils import error
from sub_def.validation import login_check

# エントリポイントとして UTF-8 出力を強制する。
# ※ utils.py が dispatch_function をインポートする際にも実行されるが実害はない。
sys.stdout.reconfigure(encoding="utf-8")

# ====================================================================================#
# ルーティングマップ
# "mode名": ("モジュールパス", "関数名")
#
# 遅延インポート方式を採用: 起動時に全モジュールをロードせず、
# リクエストに対応する 1 モジュールだけを importlib で動的ロードすることで
# 起動コストとメモリ使用量を抑える。
# ====================================================================================#
FUNCTION_MAP: dict[str, tuple[str, str]] = {
    "my_page": ("cgi_py.my_page", "my_page"),
    "my_page2": ("cgi_py.my_page2", "my_page2"),
    "change": ("cgi_py.change", "change"),
    "comment": ("cgi_py.comment", "comment"),
    "zukan": ("cgi_py.zukan", "zukan"),
    "books": ("cgi_py.books", "books"),
    "book_read": ("cgi_py.books", "book_read"),
    "yadoya": ("cgi_py.yadoya", "yadoya"),
    "kyoukai": ("cgi_py.kyoukai", "kyoukai"),
    "medal_shop": ("cgi_py.shop_base", "medal_shop"),
    "medal_shop_ok": ("cgi_py.medal_shop", "medal_shop_ok"),
    "name_change": ("cgi_py.name_change", "name_change"),
    "name_change_ok": ("cgi_py.name_change", "name_change_ok"),
    "seitenkan_ok": ("cgi_py.seitenkan", "seitenkan_ok"),
    "park": ("cgi_py.park", "park"),
    "park_1": ("cgi_py.park", "park_1"),
    "park_2": ("cgi_py.park", "park_2"),
    "v_shop": ("cgi_py.shop_base", "v_shop"),
    "v_shop_ok": ("cgi_py.v_shop", "v_shop_ok"),
    "v_shop2": ("cgi_py.shop_base", "v_shop2"),
    "v_shop2_ok": ("cgi_py.v_shop2", "v_shop2_ok"),
    "haigou_check": ("cgi_py.haigou_check", "haigou_check"),
    "haigou_hensin": ("cgi_py.haigou_hensin", "haigou_hensin"),
    "battle_type": ("cgi_py.battle.battle_type", "battle_type"),
    "battle_type2": ("cgi_py.battle.battle_type", "battle_type2"),
    "battle_fight": ("cgi_py.battle.battle_fight", "battle_fight"),
    "m_get": ("cgi_py.m_get", "m_get"),
    "m_bye": ("cgi_py.m_bye", "m_bye"),
    "roomkey_get": ("cgi_py.roomkey_get", "roomkey_get"),
    "omiai_room": ("cgi_py.omiai.omiai_room", "omiai_room"),
    "omiai_touroku": ("cgi_py.omiai.omiai_touroku", "omiai_touroku"),
    "omiai_touroku_cancel": ("cgi_py.omiai.omiai_touroku", "omiai_touroku_cancel"),
    "omiai_request": ("cgi_py.omiai.omiai_request", "omiai_request"),
    "omiai_request_ok": ("cgi_py.omiai.omiai_request", "omiai_request_ok"),
    "omiai_request_cancel": ("cgi_py.omiai.omiai_request", "omiai_request_cancel"),
    "omiai_answer_no": ("cgi_py.omiai.omiai_answer", "omiai_answer_no"),
    "omiai_answer_ok": ("cgi_py.omiai.omiai_answer", "omiai_answer_ok"),
    "omiai_answer_result": ("cgi_py.omiai.omiai_answer", "omiai_answer_result"),
    "omiai_baby_get": ("cgi_py.omiai.omiai_baby", "omiai_baby_get"),
    "number_unit": ("cgi_py.number_unit", "number_unit"),
}

# GET リクエストを許可する例外モード。
# frozenset で O(1) 検索 + イミュータブルであることを型で明示する。
_ALLOWED_GET_MODES: frozenset[str] = frozenset({"my_page2", "zukan"})


# ====================================================================================#
def load_module(module_path: str) -> types.ModuleType:
    """モジュールパスを受け取り、動的インポートして返す"""
    return importlib.import_module(module_path)


def dispatch_function(form: dict) -> None:
    """
    FUNCTION_MAP を参照して対応する CGI ハンドラ関数を呼び出す。
    各ハンドラは内部で print_html / error / success のいずれかを呼び sys.exit() する。
    """
    mode = form.get("mode")
    if mode not in FUNCTION_MAP:
        error(f"無効なモードです: {mode}", "top")

    module_path, func_name = FUNCTION_MAP[mode]
    try:
        module = load_module(module_path)
        func = getattr(module, func_name)

        if not callable(func):
            error(f"システムエラー: ルーティング設定が不正です", "top")

        func(form)

    except (ImportError, AttributeError) as e:
        # 情報漏洩防止のためスタックトレースはサーバーログ(stderr)にのみ書き出す
        print(
            f"[Routing Error] モジュール/関数の読み込み失敗 '{mode}': {e}",
            file=sys.stderr,
        )
        error("システムエラー: 要求された機能が見つかりません。", "top")

    except Exception as e:
        # 情報漏洩防止のためスタックトレースはサーバーログ(stderr)に流し、
        # ユーザーには安全なメッセージだけを見せる
        traceback.print_exc(file=sys.stderr)
        error("システム処理中に予期せぬエラーが発生しました。", "top")


def process_form() -> None:
    """フォームデータを処理し、認証と関数ディスパッチを実行する"""
    form = cgi.FieldStorage()

    # 複数パラメータ送信によるリスト化（型エラー）を防ぐため getfirst を使用
    FORM = {key: form.getfirst(key) for key in form}

    # パラメーターによるセーブデータフォルダ分岐処理
    conf.apply_fol(FORM)

    # メンテナンスモードチェック
    if os.path.exists("mente.mente"):
        error("現在メンテナンス中です。後で再度お試しください", "top")

    mode = FORM.get("mode", "")
    request_method = os.environ.get("REQUEST_METHOD", "GET")

    if request_method != "POST":
        if mode in _ALLOWED_GET_MODES:
            dispatch_function(FORM)
            # dispatch_function は内部で sys.exit() を呼ぶが、
            # 万が一ハンドラが正常返した場合に備えた安全網として明示的に終了する
            sys.exit()

        error("無効なリクエストです (POST通信が必要です)", "top")

    # 認証とトークンチェック
    session = get_session()
    login_data = None

    is_login_attempt = (
        session.get("ref") == "top"
        and bool(FORM.get("user_name"))
        and bool(FORM.get("password"))
    )

    has_authenticated_session = bool(session.get("in_name"))

    if is_login_attempt:
        login_data = login_check(FORM)
    elif has_authenticated_session:
        pass
    else:
        error(
            "ログイン状態が無効です。トップページからログインし直してください。", "top"
        )

    FORM["s"] = token_check(FORM, session, login_data)

    dispatch_function(FORM)


# ====================================================================================#

if __name__ == "__main__":
    try:
        process_form()
    except Exception as e:
        # ルーティング前に落ちた場合の最終安全網
        traceback.print_exc(file=sys.stderr)
        error("致命的なシステムエラーが発生しました。", "top")
