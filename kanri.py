#!D:\Python\Python314\python.exe

# kanri.py - 管理ページあれこれ

import sys
import cgi
import os
import datetime
import shutil
import secrets
import json
import random
import copy
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, NoReturn

from cgi_py import csv_to_pickle, pickle_to_csv, haigou_list_make
from sub_def.crypto import hash_password, get_session, set_session
from sub_def.file_ops import (
    open_key_dat,
    open_tokugi_dat,
    open_monster_dat,
    open_user_list,
    save_user_list,
    open_omiai_list,
    save_omiai_list,
    open_user_all,
    save_user_all,
)
from sub_def.monster_ops import monster_select
from sub_def.user_ops import delete_user, backup

from sub_def.utils import error, print_html, success, get_and_clear_flash
from sub_def.validation import (
    newpass_check,
    present_monster_check,
    present_check,
    admin_check,
)
import register
import exLock
import conf

Conf = conf.Conf
datadir = Conf["savedir"]
progress_file = os.path.join(datadir, "progress.json")

# エントリポイントとして UTF-8 出力を強制する
# 自動でutf-8にエンコードされて出力される
sys.stdout.reconfigure(encoding="utf-8")


# ==============#
# 	進捗状況表示 #
# ==============#
def process_batch(
    users: list,
    process_func: Callable[[Any], Any],
    result_collector: dict | None = None,
    batch_size: int = 10,
) -> list[str]:
    """
    ユーザー群をマルチスレッドで並列処理し、進捗を JSON ファイルに記録する。

    Args:
        users           : 処理対象のユーザーリスト（文字列または辞書のリスト）
        process_func    : ユーザー1件を処理する関数。戻り値が result_collector に格納される
        result_collector: 処理結果を蓄積する辞書（None の場合は結果を収集しない）
        batch_size      : 進捗ファイルを更新する間隔（件数）
    Returns:
        エラーメッセージの一覧（正常終了した場合は空リスト）
    """
    total_users = len(users)
    progress = {"total": total_users, "completed": 0, "status": "running"}
    last_written = 0  # 最後に進捗を書き込んだ完了数
    errors: list[str] = []

    # CPUコア数に合わせてスレッドを展開（負荷分散）
    with ThreadPoolExecutor(max_workers=min(6, os.cpu_count() or 4)) as executor:
        futures = {executor.submit(process_func, user): user for user in users}
        completed = 0

        for future in as_completed(futures):
            user_info = futures[future]  # 辞書全体

            try:
                result_data = future.result()
                if result_collector is not None and result_data is not None:
                    user_name = (
                        user_info.get("user_name")
                        if isinstance(user_info, dict)
                        else str(user_info)
                    )
                    if user_name:
                        result_collector[user_name] = result_data
            except Exception as e:
                # 誰か1人のデータ破損で全体の処理が止まらないようエラーを記録して続行
                user_name = (
                    user_info.get("user_name")
                    if isinstance(user_info, dict)
                    else str(user_info)
                )
                errors.append(
                    f"ユーザー {user_name} の処理中にエラー: {type(e).__name__}: {e}"
                )
            finally:
                completed += 1
                # バッチサイズごとに進捗ファイル(JSON)を更新し、Ajaxのプログレスバーに反映させる
                if completed - last_written >= batch_size or completed == total_users:
                    progress["completed"] = completed
                    try:
                        with open(progress_file, mode="w", encoding="utf-8") as ff:
                            json.dump(progress, ff)
                        last_written = completed
                    except Exception as e:
                        errors.append(f"進捗ファイル書き込みエラー: {e}")

    # 処理完了後は進捗ファイルを削除
    try:
        if os.path.exists(progress_file):
            os.remove(progress_file)
    except Exception:
        pass

    return errors


# ==================#
# confオーバーライド #
# ==================#
def update_conf_value(key: str, value: Any) -> None:
    """設定ファイル(JSON)を動的に書き換える処理（イベントブースト等で使用）"""
    path = Conf["override_file"]

    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}

    data[key] = value

    # 安全なファイル更新（一時ファイルを作ってからリネーム上書きし、破損を防ぐ）
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    os.replace(tmp, path)

    # ファイルだけでなく、現在動いているメモリ上の「Conf」も即座に同期させる
    Conf[key] = value


# ==============#
# 	管理モード	#
# ==============#
def OPEN_K() -> NoReturn:
    print_html("kanri_login_tmp.html", {"Conf": Conf, "token": FORM["s"]["token"]})


def KANRI() -> NoReturn:
    token = FORM["s"]["token"]
    u_list = open_user_list()

    # Flashメッセージの取得とクリア（一番最初に呼ぶ）
    flash_msg, flash_type = get_and_clear_flash(FORM["s"])

    mente_chek = True if os.path.exists("mente.mente") else None

    # テンプレートに渡すデータ
    data = {
        "mente_chek": mente_chek,
        "users": u_list,
        "token": token,
        "Conf": Conf,
        "flash_msg": flash_msg,
        "flash_type": flash_type,
    }

    print_html("kanri_tmp.html", data)


# ====================#
# メンテナンスモード   #
# ====================#
def MENTE() -> NoReturn:
    # MAINTENANCE_MODE はこの関数から書き込まれるが、
    # 実際のメンテ判定は各ページで os.path.exists("mente.mente") を直接見ているため
    # 参照側での利用はない。将来の拡張用として保持する。
    global MAINTENANCE_MODE

    mente_path = "mente.mente"

    # mente.mente という空ファイルの有無でメンテナンス状態を判定するフラグ管理
    if FORM["mente"] == "start":
        if not os.path.exists(mente_path):
            os.makedirs(mente_path, exist_ok=True)
        MAINTENANCE_MODE = True
        txt = "メンテナンスモードに入りました。"
    else:
        if os.path.exists(mente_path):
            try:
                os.rmdir(mente_path)
            except OSError as e:
                error(f"メンテナンスモードの解除に失敗しました: {e}", "kanri")
        MAINTENANCE_MODE = False
        txt = "メンテナンスモードを終了しました。"

    success(txt, jump="kanri")


# ========================#
# イベントブーストモード   #
# ========================#
def event_boost() -> NoReturn:
    if FORM["event_boost"] == "start":
        val = 1
        txt = "イベントブーストモードに入りました。"
    else:
        val = 0
        txt = "イベントブーストモードを終了しました。"

    update_conf_value("event_boost", val)
    success(txt, jump="kanri")


# =========#
# 強制登録 #
# =========#
def NEW() -> NoReturn:
    register.sinki(FORM, True)


# ================#
# パスワード変更  #
# ================#
def NEWPASS() -> NoReturn:
    target_name = FORM.get("target_name")

    # 未選択時のクラッシュ防止
    if not target_name:
        error("対象ユーザーが選択されていません。", "kanri")

    newpass = FORM.get("newpass")
    newpass_check(FORM)

    crypted = hash_password(newpass)

    all_data = open_user_all(target_name)
    # セーブデータが空だった場合のKeyError防止（setdefault）
    user = all_data.setdefault("user", {})
    user["pass"] = crypted

    save_user_all(all_data, target_name)

    # ログイン判定に使われる user_list 側も同期して書き換える
    u_list = open_user_list()
    if target_name in u_list:
        u_list[target_name]["pass"] = crypted
        save_user_list(u_list)

    success(
        f"管理モードで<span>{target_name}</span>のパスワードを変更しました",
        jump="kanri",
    )


# =============#
# ユーザー削除 #
# =============#
def DEL() -> NoReturn:
    target_name = FORM.get("target_name")

    if FORM.get("Del_ck") != "on":
        error("確認チェックがONになっていません。", "kanri")
    if not target_name:
        error("対象ユーザーが選択されていません。", "kanri")

    delete_user(target_name)

    # user_list.pickle からも対象者を消去
    u_list = open_user_list()
    u_list.pop(target_name, None)
    save_user_list(u_list)

    success(f"<span>{target_name}</span>を管理モードで強制削除しました", jump="kanri")


# =================#
# saveフォルダ削除 #
# =================#
def data_del() -> None:
    # 削除前に念のためバックアップを実行
    backup()

    shutil.rmtree(datadir)
    os.makedirs(datadir)

    with open(datadir + "/bbslog.log", mode="w", encoding="utf-8_sig") as f:
        f.write("")

    open_user_list()
    open_omiai_list()


# ===========#
# リスタート #
# ===========#
def RESTART() -> NoReturn:
    if FORM.get("Reset_ck") != "on":
        error("確認チェックがONになっていません。", "kanri")

    byeday = (
        datetime.datetime.now() + datetime.timedelta(days=Conf["goodbye"])
    ).strftime("%Y-%m-%d")

    # 初期配布モンスターの候補
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

    # デフォルトの空データを生成（全ユーザーで共通のベースを1回だけ作り、各ユーザーでコピーして使う）
    default_key_base = {k: {"no": v["no"], "get": 0} for k, v in open_key_dat().items()}
    default_waza_base = {
        name: {"no": v["no"], "type": v["type"], "get": 0}
        for name, v in open_tokugi_dat().items()
    }
    default_waza_base["通常攻撃"]["get"] = 1

    default_zukan_base = {
        k: {"no": v["no"], "m_type": v["m_type"], "get": 0}
        for k, v in open_monster_dat().items()
    }

    def re_start_sub(user_info: dict) -> dict | None:
        """1ユーザーのデータをリセットして user_list 用の辞書を返す"""
        try:
            user_name = user_info["user_name"]
            crypted = user_info.get("crypted", "")

            m_name = random.choice(monset)

            # ユーザーの全データを初期状態にリセット
            all_data = {
                "user": {
                    "name": user_name,
                    "pass": crypted,
                    "key": 1,
                    "money": 100,
                    "medal": 0,
                    "isekai_limit": 0,
                    "isekai_key": 1,
                    "mes": "未登録",
                    "getm": "0／0匹(0％)",
                },
                "party": [
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
                        "sex": random.choice(Conf.get("sex", ["オス", "メス"])),
                    }
                ],
                "vips": {"パーク": 0},
                "room_key": copy.deepcopy(default_key_base),
                "waza": copy.deepcopy(default_waza_base),
                "zukan": copy.deepcopy(default_zukan_base),
                "park": [],
                "updated_at": datetime.datetime.now().isoformat(),
            }

            save_user_all(all_data, user_name)

            return {
                "pass": crypted,
                "host": "",
                "bye": byeday,
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
                "money": 100,
                "mes": "未登録",
                "getm": "0／0匹(0％)",
            }

        except Exception as e:
            print(
                f"リスタート失敗 {user_info.get('user_name', 'Unknown')}: {e}",
                file=sys.stderr,
            )
            return None

    u_list = open_user_list()
    users = [
        {"user_name": name, "crypted": info.get("pass", "")}
        for name, info in u_list.items()
    ]

    # 並列処理で全ユーザーデータを再生成
    new_userlist: dict = {}
    errors = process_batch(users, re_start_sub, result_collector=new_userlist)

    save_user_list(new_userlist)
    save_omiai_list({})

    msg = "ゲームを初期化、リスタートしました。"
    if errors:
        msg += "<br><br>一部エラーが発生しました。<br>" + "<br>".join(errors)

    success(msg, jump="kanri")


# =======#
# 初期化 #
# =======#
def ALLDEL() -> NoReturn:
    if FORM["Reset_ck"] != "on":
        error("確認チェックがONになっていません。", "kanri")

    data_del()
    success("全データを削除しました。", jump="kanri")


# ====================#
# ユーザーデータ再構築 #
# user_list.pickle    #
# ====================#
def FUKUGEN() -> NoReturn:
    # 各ユーザーのフォルダからデータを読み込み、全体のリスト(user_list.pickle)を作り直す
    files = os.listdir(datadir)
    exclude_dirs = {"locks", "logs"}
    user_dirs = [
        f
        for f in files
        if os.path.isdir(os.path.join(datadir, f)) and f not in exclude_dirs
    ]

    bye_day = (
        datetime.datetime.now() + datetime.timedelta(days=Conf["goodbye"])
    ).strftime("%Y-%m-%d")

    new_userlist: dict = {}

    def process_user_wrapper(in_name: str) -> dict | None:
        """1ユーザーのフォルダから user_list エントリ用辞書を生成して返す"""
        try:
            all_data = open_user_all(in_name)
            user = all_data.get("user", {})
            pt = all_data.get("party", [])

            # リストの範囲外アクセスや、キーが存在しない場合（データ破損時）のKeyErrorを防ぐ安全な取得関数
            def get_pt_val(index: int, key: str, default: Any = "") -> Any:
                if len(pt) > index and isinstance(pt[index], dict):
                    return pt[index].get(key, default)
                return default

            return {
                "pass": user.get("pass", ""),
                "host": "",
                "bye": bye_day,
                "m1_name": get_pt_val(0, "name"),
                "m1_hai": get_pt_val(0, "hai", 0),
                "m1_lv": get_pt_val(0, "lv", 0),
                "m2_name": get_pt_val(1, "name"),
                "m2_hai": get_pt_val(1, "hai", ""),
                "m2_lv": get_pt_val(1, "lv", ""),
                "m3_name": get_pt_val(2, "name"),
                "m3_hai": get_pt_val(2, "hai", ""),
                "m3_lv": get_pt_val(2, "lv", ""),
                "key": user.get("key", 0),
                "money": user.get("money", 0),
                "getm": user.get("getm", "0／0匹(0％)"),
                "mes": user.get("mes", ""),
            }
        except Exception as e:
            return None

    errors = process_batch(
        user_dirs,
        process_user_wrapper,
        result_collector=new_userlist,
    )
    save_user_list(new_userlist)

    msg = "ユーザー登録データ(user_list.pickle)を再構築しました。"
    if errors:
        msg += "<br><br>一部エラーが発生しました。<br>" + "<br>".join(errors)

    success(msg, jump="kanri")


# ====================#
# モンスター配布      #
# ====================#
def MON_PRESENT() -> NoReturn:
    target_name = FORM.get("target_name", "")

    if target_name == "":
        error("対象ユーザーが選択されていません。", "kanri")

    M_list = open_monster_dat()

    # Python側でHTMLタグを作らず、モンスター名のリスト（配列）だけをHTMLへ渡す。
    # こうすることでMVCモデルの独立性が保たれ、Jinja2によるエスケープ漏れ（表示バグ）も防げる
    monster_names = list(M_list.keys())

    context = {
        "target_name": target_name,
        "monster_names": monster_names,
        "token": FORM["s"]["token"],
        "Conf": Conf,
    }

    print_html("kanri_mon_present_tmp.html", context)


# ====================#
# モンスター配布 処理 #
# ====================#
def MON_PRESENT_OK() -> NoReturn:
    target_name = FORM["target_name"]
    mons_name = FORM.get("mons_name")
    sex = FORM.get("sex")
    max_level = int(FORM.get("max_level", 10))
    haigou = int(FORM.get("haigou", 0))

    present_monster_check(FORM)

    all_data = open_user_all(target_name)
    party = all_data.get("party", [])

    if len(party) >= 10:
        error("パーティがいっぱいで追加することができません。", "kanri")

    # 指定されたステータスで新しいモンスターのデータフレームを生成
    new_mob = monster_select(mons_name, haigou)
    new_mob["lv"] = 1
    new_mob["mlv"] = max_level
    new_mob["sex"] = sex
    new_mob["hai"] = haigou

    party.append(new_mob)

    # パーティの並び順(no)を再採番する
    for i, pt in enumerate(party, 1):
        pt["no"] = i

    all_data["party"] = party
    save_user_all(all_data, target_name)

    success(f"{target_name}へモンスターを配布しました", jump="kanri")


# ====================#
# プレゼント          #
# ====================#
def PRESENT() -> NoReturn:
    target_name = FORM.get("target_name", "")

    present_check(FORM)

    money = int(FORM.get("money", 0))
    medal = int(FORM.get("medal", 0))
    key = int(FORM.get("key", 0))

    def haifu(name: str) -> None:
        """1ユーザーへお金・メダル・鍵を加算して保存する"""
        all_data = open_user_all(name)
        user = all_data.get("user", {})
        user["money"] = user.get("money", 0) + money
        user["medal"] = user.get("medal", 0) + medal
        user["key"] = user.get("key", 0) + key
        all_data["user"] = user
        save_user_all(all_data, name)

    # 「全員」が選択された場合は並列バッチ処理で一斉配布する
    if target_name == "全員":
        u_list = open_user_list()
        errors = process_batch(list(u_list.keys()), haifu)

        msg = "全員にプレゼントを送りました。"
        if errors:
            msg += "<br><br>一部エラーが発生しました。<br>" + "<br>".join(errors)

        success(msg, jump="kanri")

    else:
        haifu(target_name)
        success(f"{target_name}にプレゼントを送りました。", jump="kanri")


# ====================#
# csv → pickle       #
# ====================#
def csv_to() -> NoReturn:
    target_name = FORM.get("target_name")

    if not target_name:
        error("対象が選択されていません。", "kanri")

    csv_to_pickle.csv_to_pickle(target_name)
    success(f"{target_name}のcsv→pickle変換が完了しました。", jump="kanri")


# ====================#
# pickle → csv       #
# ====================#
def pickle_to() -> NoReturn:
    target_name = FORM.get("target_name")

    if not target_name:
        error("対象が選択されていません。", "kanri")

    backup()
    pickle_to_csv.pickle_to_csv(target_name)
    success(f"{target_name}のpickle→csv変換が完了しました。", jump="kanri")


# ================#
# save_edit      #
# ================#
def make_table(save_data: list | dict, txt: str) -> NoReturn:
    """セーブデータをテーブル形式で編集画面に表示する"""
    target_name = FORM.get("target_name")
    target_data = FORM.get("target_data")

    # フォーム上で編集不可（表示のみ）にするカラムの設定
    no_edit = ("no", "user_name", "pass", "type", "m_type", "host", "rank", "getm")

    # データ構造の統一（辞書形式の場合はリスト形式に変換してHTMLの表で扱いやすくする）
    if isinstance(save_data, dict) and all(
        isinstance(v, dict) for v in save_data.values()
    ):
        rows = [{"name": k, **v} for k, v in save_data.items()]
    else:
        rows = save_data if isinstance(save_data, list) else [save_data]

    # データが空っぽ（[]）だった場合、アクセスエラー(IndexError)になる前に弾く安全対策
    if not rows:
        error(
            f"{target_name}の「{txt}」は現在空っぽです。<br>編集するデータがありません。",
            "kanri",
        )

    context = {
        "txt": txt,
        "headers": list(rows[0].keys()),
        "rows": rows,
        "no_edit": no_edit,
        "target_name": target_name,
        "target_data": target_data,
        "token": FORM["s"]["token"],
        "Conf": Conf,
    }

    print_html("kanri_saveedit_table_tmp.html", context)


def save_editer() -> NoReturn:
    target_name = FORM.get("target_name")
    target_data = FORM.get("target_data")

    if not target_name:
        error("対象が選択されていません。", "kanri")

    # 対象の種類によって読み込むデータソースを分岐
    match target_name:
        case "user_list":
            save_data = open_user_list()
            if not save_data:
                error("現在登録者はいないようです。<br>編集できません。", "kanri")
            save_data = [{"user_name": u} | v for u, v in save_data.items()]
            txt = "登録ユーザーリスト"
        case "omiai_list":
            save_data = open_omiai_list()
            if not save_data:
                error(
                    "現在お見合い登録者はいないようです。<br>編集できません。", "kanri"
                )
            save_data = [{"user_name": u} | v for u, v in save_data.items()]
            txt = "お見合いリスト"
        case _:
            all_data = open_user_all(target_name)
            match target_data:
                case "user_data":
                    save_data = all_data.get("user", {})
                    txt = "ユーザー情報"
                case "party_data":
                    save_data = all_data.get("party", [])
                    txt = "パーティーデータ"
                case "room_key_data":
                    save_data = [
                        {"name": k, **v}
                        for k, v in all_data.get("room_key", {}).items()
                    ]
                    txt = "部屋の鍵データ"
                case "waza_data":
                    save_data = [
                        {"name": k, **v} for k, v in all_data.get("waza", {}).items()
                    ]
                    txt = "習得特技データ"
                case "zukan_data":
                    save_data = [
                        {"name": k, **v} for k, v in all_data.get("zukan", {}).items()
                    ]
                    txt = "図鑑データ"
                case "park_data":
                    save_data = all_data.get("park", [])
                    txt = "モンスターパークデータ"
                    if not save_data:
                        error(
                            "現在パーク内にモンスターはいないようです。<br>編集できません。",
                            "kanri",
                        )
                case "vips_data":
                    save_data = all_data.get("vips", {})
                    txt = "その他データ"
                case _:
                    error("不明なtarget_dataです", "kanri")

    if isinstance(save_data, list):
        make_table(save_data, txt)
    else:
        make_table([save_data], txt)


def save_edit_select() -> NoReturn:
    target_name = FORM.get("target_name")
    if not target_name:
        error("対象が選択されていません。", "kanri")

    context = {"target_name": target_name, "token": FORM["s"]["token"], "Conf": Conf}

    if target_name in ("user_list", "omiai_list"):
        save_editer()
    else:
        print_html("kanri_saveedit_select_tmp.html", context)


def save_edit_save() -> NoReturn:
    target_name = FORM["target_name"]
    target_data = FORM["target_data"]

    def get_typed_val(form_val: Any, old_val: Any) -> Any:
        """
        元のデータの型(intかstrか)に合わせて安全にキャストするヘルパー関数。
        すべてを盲目的にint()にキャストしてしまうと、パスワードや文字列のユーザー名が
        数値化されてしまい、データが完全に破損して二度とログインできなくなるのを防ぐ。
        """
        if form_val is None:
            return old_val
        if isinstance(old_val, int):
            try:
                return int(form_val)
            except ValueError:
                return form_val
        return form_val

    # 各種セーブデータの保存処理（get_typed_val を使って型を維持したまま上書きする）
    if target_name == "user_list":
        txt = "ユーザーリストを更新しました。"
        original = open_user_list()
        updated = {}
        for i in range(len(original)):
            user_name = str(FORM.get(f"{i},user_name", ""))
            if user_name and user_name in original:
                updated[user_name] = {
                    k: get_typed_val(FORM.get(f"{i},{k}"), original[user_name].get(k))
                    for k in original[user_name].keys()
                }
        save_user_list(updated)
        success(txt, jump="kanri")
        # success() は NoReturn のためここには到達しない（型チェッカー向け）
        raise RuntimeError("unreachable")

    if target_name == "omiai_list":
        txt = "お見合いリストを更新しました。"
        original = open_omiai_list()
        updated = {}
        for i in range(len(original)):
            user_name = str(FORM.get(f"{i},user_name", ""))
            if user_name and user_name in original:
                updated[user_name] = {
                    k: get_typed_val(FORM.get(f"{i},{k}"), original[user_name].get(k))
                    for k in original[user_name].keys()
                }
        save_omiai_list(updated)
        success(txt, jump="kanri")
        # success() は NoReturn のためここには到達しない（型チェッカー向け）
        raise RuntimeError("unreachable")

    all_data = open_user_all(target_name)

    match target_data:
        case "user_data":
            txt = "ユーザー情報"
            user = all_data.get("user", {})
            for k in list(user.keys()):
                user[k] = get_typed_val(FORM.get(f"0,{k}"), user.get(k))
            all_data["user"] = user

        case "vips_data":
            txt = "その他データ"
            vips = all_data.get("vips", {})
            for k in list(vips.keys()):
                vips[k] = get_typed_val(FORM.get(f"0,{k}"), vips.get(k))
            all_data["vips"] = vips

        case "room_key_data":
            txt = "部屋の鍵データ"
            room_key = {}
            i = 0
            while f"{i},name" in FORM:
                name = FORM[f"{i},name"]
                if name:
                    old_data = all_data.get("room_key", {}).get(name, {})
                    room_key[name] = {
                        k: get_typed_val(FORM.get(f"{i},{k}"), old_data.get(k))
                        for k in old_data.keys()
                    }
                i += 1
            all_data["room_key"] = room_key

        case "waza_data":
            txt = "習得特技データ"
            waza = {}
            i = 0
            while f"{i},name" in FORM:
                name = FORM[f"{i},name"]
                if name:
                    old_data = all_data.get("waza", {}).get(name, {})
                    waza[name] = {
                        k: get_typed_val(FORM.get(f"{i},{k}"), old_data.get(k))
                        for k in old_data.keys()
                    }
                i += 1
            all_data["waza"] = waza

        case "zukan_data":
            txt = "図鑑データ"
            zukan = {}
            i = 0
            while f"{i},name" in FORM:
                name = FORM[f"{i},name"]
                if name:
                    old_data = all_data.get("zukan", {}).get(name, {})
                    zukan[name] = {
                        k: get_typed_val(FORM.get(f"{i},{k}"), old_data.get(k))
                        for k in old_data.keys()
                    }
                i += 1
            all_data["zukan"] = zukan

        case "party_data":
            txt = "パーティーデータ"
            party = all_data.get("party", [])
            for i in range(len(party)):
                for k in list(party[i].keys()):
                    party[i][k] = get_typed_val(FORM.get(f"{i},{k}"), party[i].get(k))
            all_data["party"] = party

        case "park_data":
            txt = "モンスターパークデータ"
            park = all_data.get("park", [])
            for i in range(len(park)):
                for k in list(park[i].keys()):
                    park[i][k] = get_typed_val(FORM.get(f"{i},{k}"), park[i].get(k))
            all_data["park"] = park

        case _:
            error("不明なtarget_dataです", "kanri")

    save_user_all(all_data, target_name)
    success(f"{target_name}の{txt}を更新しました。", jump="kanri")


# ================#
# dat_update     #
# ================#
def update_isekai_limit(M_list: dict) -> None:
    """異世界最深部設定を更新"""
    # マスターデータから一番深い階層を調べ、confオーバーライドファイルに保存する
    isekai_max_limit = max(
        [mon["階層B"] for mon in M_list.values() if (mon["room"] in ("異世界"))]
    )

    update_conf_value("isekai_max_limit", isekai_max_limit)


def dat_update_check(in_name: str, M_list: dict, Tokugi_dat: dict) -> None:
    """ユーザーの図鑑と技データをマスターデータに沿って更新（枠の追加など）"""
    all_data = open_user_all(in_name)
    user = all_data.get("user", {})
    zukan = all_data.get("zukan", {})
    waza = all_data.get("waza", {})

    # 新モンスターが追加された場合など、図鑑の枠データを再構築
    new_zukan = {
        name: {
            "no": mon["no"],
            "m_type": mon["m_type"],
            "get": zukan.get(name, {}).get("get", 0),
        }
        for name, mon in M_list.items()
    }
    all_data["zukan"] = new_zukan

    # 特技数が変化した場合に技データを再構築
    if len(Tokugi_dat) != len(waza):
        new_waza = {
            name: {
                "no": v["no"],
                "type": v["type"],
                "get": waza.get(name, {}).get("get", 0),
            }
            for name, v in Tokugi_dat.items()
        }
        all_data["waza"] = new_waza

    # 取得率(getm)の再計算と更新
    get = sum(v.get("get") == 1 for v in new_zukan.values())
    mleng = len(new_zukan)
    user["getm"] = (
        f"{get}／{mleng}匹 ({get / mleng * 100:.2f}％)" if mleng > 0 else "0／0匹(0％)"
    )

    save_user_all(all_data, in_name)


def dat_update() -> NoReturn:
    """データファイルを更新し、全ユーザー情報へ反映"""
    # CSVからpickleへマスターデータを変換
    for target_key in Conf.get("csv_defs_master", {}).keys():
        csv_to_pickle.convert_csv_to_pickle(target_key)

    # 配合リスト2種を作り直す
    haigou_list_make.haigou_list_make()

    M_list = open_monster_dat()
    Tokugi_dat = open_tokugi_dat()

    # 異世界最深部設定の更新
    update_isekai_limit(M_list)

    def process_user(name: str) -> None:
        dat_update_check(name, M_list, Tokugi_dat)

    u_list = open_user_list()
    # ユーザー全員のデータを並列バッチ処理で高速に更新
    errors = process_batch(list(u_list.keys()), process_user)

    msg = "datファイルの更新を反映しました。"
    if errors:
        msg += "<br><br>一部エラーが発生しました。<br>" + "<br>".join(errors)

    success(msg, jump="kanri")


# ================#
# cgi_python     #
# ================#
def make_haigou_list() -> NoReturn:
    """手動で配合リスト2種を作り直す"""
    haigou_list_make.haigou_list_make()
    success("配合リストHTMLを作成しました。", jump="kanri")


# ============================================================#
def token_check() -> dict:
    """
    CSRF攻撃や二重送信を防ぐためのワンタイムトークン照合処理。
    検証に失敗した場合は error() (NoReturn) を呼んで処理を中断する。
    """
    session = get_session()
    form_token = FORM.get("token", "")
    session_token = session.get("token", "")

    if not form_token or not secrets.compare_digest(session_token, form_token):
        error("トークンが一致しないです", "kanri")

    # 新しいトークンを発行してセッションを更新
    token = secrets.token_hex(16)
    session.update(
        {
            "token": token,
            "m_name": FORM.get("m_name", session.get("m_name", "")),
            "m_password": FORM.get("m_password", session.get("m_password", "")),
        }
    )
    set_session(session)

    return session


# FUNCTION_MAP: mode 文字列 → ハンドラ関数の対応表。
# 各関数はグローバル FORM を参照するため引数なしで呼び出す。
FUNCTION_MAP: dict[str, Callable[[], Any]] = {
    "OPEN_K": OPEN_K,
    "KANRI": KANRI,
    "MENTE": MENTE,
    "event_boost": event_boost,
    "NEW": NEW,
    "NEWPASS": NEWPASS,
    "DEL": DEL,
    "RESTART": RESTART,
    "ALLDEL": ALLDEL,
    "FUKUGEN": FUKUGEN,
    "MON_PRESENT": MON_PRESENT,
    "MON_PRESENT_OK": MON_PRESENT_OK,
    "PRESENT": PRESENT,
    "csv_to": csv_to,
    "pickle_to": pickle_to,
    "save_editer": save_editer,
    "save_edit_select": save_edit_select,
    "save_edit_save": save_edit_save,
    "dat_update": dat_update,
    "make_haigou_list": make_haigou_list,
}
# ============================================================#

if __name__ == "__main__":

    # フォームを辞書化
    form = cgi.FieldStorage()
    FORM = {key: form.getvalue(key) for key in form.keys()}

    if "mode" not in FORM:
        FORM["s"] = {"token": secrets.token_hex(16)}
        set_session(FORM["s"])
        OPEN_K()
        # OPEN_K() は NoReturn（print_html 経由で sys.exit()）のため到達しない

    # 直接URLを叩かれた場合のブロック
    if os.environ["REQUEST_METHOD"] != "POST":
        error("不正ですか？by管理モード", "top")

    func = FUNCTION_MAP.get(FORM["mode"])
    if not func:
        error(f"無効なモード [{FORM['mode']}] です。", "top")

    # セキュリティチェックを通してから該当関数を実行
    FORM["s"] = token_check()
    admin_check(FORM["s"])
    func()

    # func() は FUNCTION_MAP の全関数が NoReturn のため通常到達しない。
    # 万が一の素通りに備えた安全網。
    error("あっれれ～？おっかしぃぞぉ～by管理モード")
