#!D:\Python\Python312\python.exe

import sys
import cgi
import os
import datetime
import shutil
import secrets
import ast
import fileinput
import re
import pickle
import pandas as pd
import glob
import json
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
import time


from cgi_py import csv_to_pickle, pickle_to_csv, haigou_list_make

# import sub_def
from sub_def.crypto import hash_password, get_session, set_session
from sub_def.file_ops import *
from sub_def.monster_ops import monster_select
from sub_def.user_ops import delete_user, backup
from sub_def.utils import error, print_html, print_result
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
lock = exLock.exLock(os.path.join(datadir, "lock_fol"))

sys.stdout.reconfigure(encoding="utf-8")
# 自動でutf-8にエンコードされて出力される


# ==============#
# 	進捗状況表示 #
# ==============#
def process_batch(users, process_func, result_collector=None, batch_size=10):
    # 進捗バッチ処理
    total_users = len(users)
    progress = {"total": total_users, "completed": 0, "status": "running"}
    last_written = 0  # 最後に進捗を書き込んだ完了数

    with ThreadPoolExecutor(max_workers=Conf.get("max_workers", 8)) as executor:
        futures = {executor.submit(process_func, user): user for user in users}
        completed = 0
        for future in as_completed(futures):
            user = futures[future]
            try:
                result = future.result()
                if result_collector is not None and result is not None:
                    result_collector[user] = result
                completed += 1
                # 進捗更新は batch_size または全完了時のみ
                if completed - last_written >= batch_size or completed == total_users:
                    progress["completed"] = completed
                    try:
                        with open(progress_file, mode="w", encoding="utf-8") as ff:
                            json.dump(progress, ff)
                        last_written = completed
                    except Exception as e:
                        error(f"進捗ファイル書き込みエラー: {e}", "kanri")
            except Exception as e:
                error(
                    f"ユーザー {user} の処理中にエラー: {type(e).__name__}: {e}",
                    "kanri",
                )

    delete_progress_file()


# ==============#
# 	json削除	#
# ==============#
def delete_progress_file():
    # 進捗ファイルを安全に削除
    retries = 3
    for attempt in range(retries):
        try:
            if os.path.exists(progress_file):
                with open(progress_file, "r+") as f:
                    lock.lock()
                    os.remove(progress_file)
                    lock.unlock()
            return
        except (OSError, IOError) as e:
            lock.unlock()
            if attempt < retries - 1:
                time.sleep(0.5)  # リトライ前に待機
                continue
            error(f"進捗ファイルの削除に失敗しました: {e}", "kanri")


# ==========#
# リザルト #
# ==========#
def result(txt=""):
    print_result(txt, kanri=True, token=FORM["token"])


# ==============#
# 	管理モード	#
# ==============#
def OPEN_K():
    print_html("kanri_login_tmp.html", {"token": FORM["token"]})


def KANRI():
    token = FORM["token"]
    u_list = open_user_list()

    mente_chek = True if os.path.exists("mente.mente") else None

    # テンプレートに渡すデータ
    data = {
        "mente_chek": mente_chek,
        "users": u_list,
        "token": token,
    }

    print_html("kanri_tmp.html", data)


# ====================#
# メンテナンスモード   #
# ====================#
def MENTE():
    if FORM["mente"] == "start":
        os.makedirs("mente.mente")
        txt = "メンテナンスモードに入りました。"
    else:
        if os.path.exists("mente.mente"):
            os.rmdir("mente.mente")
        txt = "メンテナンスモードを終了しました。"
    result(txt)


# ========================#
# イベントブーストモード   #
# ========================#
def event_boost():

    if FORM["event_boost"] == "start":
        val = 1
        txt = "イベントブーストモードに入りました。"
    else:
        val = 0
        txt = "イベントブーストモードを終了しました。"

    try:
        with fileinput.FileInput(
            "conf.py", inplace=True, backup=".bak", encoding="utf-8"
        ) as f:
            for line in f:
                print(
                    re.sub(
                        r"Conf\[\"event_boost\"\] = \d",
                        f'Conf["event_boost"] = {val}',
                        line,
                    ),
                    end="",
                )
    except Exception as e:
        error(f"conf.pyの更新に失敗しました: {e}", "kanri")
        return

    result(txt)


# =========#
# 強制登録 #
# =========#
def NEW():
    register.sinki(FORM, True)


# ================#
# パスワード変更  #
# ================#
def NEWPASS():
    target_name = FORM.get("target_name")
    newpass = FORM.get("newpass")

    newpass_check(FORM)

    crypted = hash_password(newpass)
    u_list = open_user_list()
    user = open_user(target_name)

    user["pass"] = crypted
    u_list[target_name]["pass"] = crypted

    save_user_list(u_list)
    save_user(user, target_name)

    result(f"管理モードで<span>{target_name}</span>のパスワードを変更しました")


# =============#
# ユーザー削除 #
# =============#
def DEL():
    target_name = FORM.get("target_name")

    if FORM.get("Del_ck") != "on":
        error("確認チェックがONになっていません。", "kanri")
    if not (target_name):
        error("対象ユーザーが選択されていません。", "kanri")

    u_list = open_user_list()

    delete_user(target_name)
    del u_list[target_name]

    save_user_list(u_list)

    result(f"<span>{target_name}</span>を管理モードで強制削除しました")


# =================#
# saveフォルダ削除 #
# =================#
def data_del():
    backup()

    shutil.rmtree(datadir)
    os.makedirs(datadir)

    with open(datadir + "/tournament.log", mode="w", encoding="utf-8") as f:
        f.write(
            """<div class="medal_battle_title">まだ大会は一度も開かれていません</div><br><br><br>"""
        )

    with open(datadir + "/bbslog.log", mode="w", encoding="utf-8_sig") as f:
        f.write("")

    open_user_list()
    open_omiai_list()


# ===========#
# リスタート #
# ===========#
def RESTART():
    if FORM.get("Reset_ck") != "on":
        error("確認チェックがONになっていません。", "kanri")

    new_userlist = {}
    byeday = (
        datetime.datetime.now() + datetime.timedelta(days=Conf["goodbye"])
    ).strftime("%Y-%m-%d")

    def create_default_data():
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
        default_key = {k: {"no": v["no"], "get": 0} for k, v in open_key_dat().items()}
        default_waza = {
            name: {"no": v["no"], "type": v["type"], "get": 0}
            for name, v in open_tokugi_dat().items()
        }
        default_waza["通常攻撃"]["get"] = 1
        default_zukan = {
            k: {"no": v["no"], "m_type": v["m_type"], "get": 0}
            for k, v in open_monster_dat().items()
        }
        return monset, default_key, default_waza, default_zukan

    def re_start_sub(u):
        try:
            monset, default_key, default_waza, default_zukan = create_default_data()
            m_name = random.choice(monset)

            new_userlist[u["user_name"]] = {
                "pass": u["crypted"],
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
                "money": 50,
                "mes": "未登録",
                "getm": 0,
            }

            # ユーザーデータ
            save_user(
                {
                    "name": u["user_name"],
                    "pass": u["crypted"],
                    "key": 1,
                    "money": 100,
                    "medal": 0,
                    "isekai_limit": 0,
                    "isekai_key": 1,
                    "mes": "未登録",
                    "getm": "0／0匹(0％)",
                },
                u["user_name"],
            )

            # パーティーデータ
            save_party(
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
                u["user_name"],
            )

            # 追加データの初期化
            save_room_key(default_key, u["user_name"])
            save_waza(default_waza, u["user_name"])
            save_zukan(default_zukan, u["user_name"])
            save_vips({"パーク": 0}, u["user_name"])
            save_park([], u["user_name"])
            return True

        except Exception as e:
            error(f"ユーザー {u['user_name']} の処理中にエラー: {e}", "kanri")
            return False

    u_list = open_user_list()
    users = [{"user_name": name, "crypted": v["pass"]} for name, v in u_list.items()]
    process_batch(users, re_start_sub)

    save_user_list(new_userlist)
    save_omiai_list({})
    result("ゲームを初期化、リスタートしました。")


# =======#
# 初期化 #
# =======#
def ALLDEL():
    if FORM["Reset_ck"] != "on":
        error("確認チェックがONになっていません。", "kanri")

    data_del()

    result("全データを削除しました。")


# ====================#
# ユーザーデータ再構築 #
# user_list.pickle    #
# ====================#
def process_user(in_name, bye_day):
    """1ユーザー分のデータを処理する関数"""
    user = open_user(in_name)
    pt = open_party(in_name)
    return {
        "pass": user["pass"],
        "host": "",
        "bye": bye_day,
        "m1_name": pt[0]["name"],
        "m1_hai": pt[0]["hai"],
        "m1_lv": pt[0]["lv"],
        "m2_hai": pt[1]["hai"] if (pt[1:2]) else "",
        "m2_lv": pt[1]["lv"] if (pt[1:2]) else "",
        "m2_name": pt[1]["name"] if (pt[1:2]) else "",
        "m3_hai": pt[2]["hai"] if (pt[2:3]) else "",
        "m3_lv": pt[2]["lv"] if (pt[2:3]) else "",
        "m3_name": pt[2]["name"] if (pt[2:3]) else "",
        "key": user["key"],
        "money": user["money"],
        "getm": user["getm"],
        "mes": user["mes"],
    }


def FUKUGEN():
    # セーブデータフォルダ内各ユーザー名取得
    files = os.listdir(datadir)
    files_dir = [f for f in files if os.path.isdir(os.path.join(datadir, f))]

    bye_day = (
        datetime.datetime.now() + datetime.timedelta(days=Conf["goodbye"])
    ).strftime("%Y-%m-%d")

    total_users = len(files_dir)  # 全体のユーザー数
    progress = {"total": total_users, "completed": 0, "status": "running"}
    with open(progress_file, mode="w", encoding="utf-8") as ff:
        json.dump(progress, ff)

    u_list = {}

    def process_user_wrapper(in_name):
        return process_user(in_name, bye_day)

    process_batch(
        files_dir,
        process_user_wrapper,
        result_collector=u_list,
    )
    save_user_list(u_list)

    result("ユーザー登録データ(user_list.pickle)を再構築しました。")


# ====================#
# モンスター配布      #
# ====================#
def MON_PRESENT():
    target_name = FORM.get("target_name", "")

    if target_name == "":
        error("対象ユーザーが選択されていません。", "kanri")

    M_list = open_monster_dat()
    txt = "".join(
        [f"""<option value={name}>{name}</option>\n""" for name in M_list.keys()]
    )

    context = {
        "target_name": target_name,
        "txt": txt,
        "token": FORM["token"],
    }

    print_html("kanri_mon_present_tmp.html", context)


# ====================#
# モンスター配布 処理 #
# ====================#
def MON_PRESENT_OK():
    target_name = FORM["target_name"]
    mons_name = FORM.get("mons_name")
    sex = FORM.get("sex")
    max_level = int(FORM.get("max_level", 10))
    haigou = int(FORM.get("haigou", 0))

    present_monster_check(FORM)

    party = open_party(target_name)

    if len(party) >= 10:
        error("パーティがいっぱいで追加することができません。", "kanri")

    new_mob = monster_select(mons_name, haigou)
    new_mob["lv"] = 1
    new_mob["mlv"] = max_level
    new_mob["sex"] = sex
    new_mob["hai"] = haigou

    party.append(new_mob)
    for i, pt in enumerate(party, 1):
        pt["no"] = i

    save_party(party, target_name)

    result(f"{target_name}へモンスターを配布しました")


# ====================#
# プレゼント          #
# ====================#
def PRESENT():
    target_name = FORM.get("target_name", "")

    present_check(FORM)

    money = int(FORM.get("money", 0))
    medal = int(FORM.get("medal", 0))
    key = int(FORM.get("key", 0))

    def haifu(name):
        user = open_user(name)
        user["money"] += int(money)
        user["medal"] += int(medal)
        user["key"] += int(key)
        save_user(user, name)

    if target_name == "全員":
        u_list = open_user_list()
        process_batch(u_list, haifu)

        result(f"全員にプレゼントを送りました。")

        delete_progress_file()

    else:
        haifu(target_name)

    result(f"{target_name}にプレゼントを送りました。")


# ====================#
# csv → pickle       #
# ====================#
def csv_to():
    # user_listや各種ユーザーデータはpickle変換後csvは削除される
    target_name = FORM.get("target_name")

    if not (target_name):
        error("対象が選択されていません。", "kanri")

    csv_to_pickle.csv_to_pickle(target_name)

    result(f"{target_name}のcsv→pickle変換が完了しました。")


# ====================#
# pickle → csv       #
# ====================#
def pickle_to():
    target_name = FORM.get("target_name")

    if not (target_name):
        error("対象が選択されていません。", "kanri")

    backup()
    pickle_to_csv.pickle_to_csv(target_name)

    result(f"{target_name}のpickle→csv変換が完了しました。")


# ================#
# save_edit      #
# ================#
def make_table(save_data, txt):
    target_name = FORM.get("target_name")
    target_data = FORM.get("target_data")
    no_edit = ("no", "user_name", "pass", "type", "m_type", "host", "rank", "getm")

    if isinstance(save_data, dict) and all(
        isinstance(v, dict) for v in save_data.values()
    ):
        # ネストされた辞書の場合
        rows = [{"name": k, **v} for k, v in save_data.items()]
    else:
        rows = save_data if isinstance(save_data, list) else [save_data]

    context = {
        "txt": txt,
        "headers": list(rows[0].keys()),
        "rows": rows,
        "no_edit": no_edit,
        "target_name": target_name,
        "target_data": target_data,
        "token": FORM["token"],
    }

    print_html("kanri_saveedit_table_tmp.html", context)


def save_editer():
    target_name = FORM.get("target_name")
    target_data = FORM.get("target_data")

    if not (target_name):
        error("対象が選択されていません。", "kanri")

    match target_name:
        case "user_list":
            save_data = open_user_list()
            if not (save_data):
                error("現在登録者はいないようです。<br>編集できません。", "kanri")
            save_data = [{"user_name": u} | v for u, v in save_data.items()]
            txt = "登録ユーザーリスト"
        case "omiai_list":
            save_data = open_omiai_list()
            if not (save_data):
                error(
                    "現在お見合い登録者はいないようです。<br>編集できません。", "kanri"
                )
            save_data = [{"user_name": u} | v for u, v in save_data.items()]
            txt = "お見合いリスト"

    match target_data:
        case "user_data":
            save_data = open_user(target_name)
            txt = "ユーザー情報"
        case "party_data":
            save_data = open_party(target_name)
            txt = "パーティーデータ"
        case "room_key_data":
            save_data = open_room_key(target_name)
            save_data = [{"name": u} | v for u, v in save_data.items()]
            txt = "部屋の鍵データ"
        case "waza_data":
            save_data = open_waza(target_name)
            save_data = [{"name": u} | v for u, v in save_data.items()]
            txt = "習得特技データ"
        case "zukan_data":
            save_data = open_zukan(target_name)
            save_data = [{"name": u} | v for u, v in save_data.items()]
            txt = "図鑑データ"
        case "park_data":
            save_data = open_park(target_name)
            txt = "モンスターパークデータ"
            if not (save_data):
                error(
                    "現在パーク内にモンスターはいないようです。<br>編集できません。",
                    "kanri",
                )
        case "vips_data":
            save_data = open_vips(target_name)
            txt = "その他データ"

    if type(save_data) == list:
        make_table(save_data, txt)
    else:
        make_table([save_data], txt)


def save_edit_select():
    target_name = FORM.get("target_name")

    if not (target_name):
        error("対象が選択されていません。", "kanri")

    context = {"target_name": target_name, "token": FORM["token"]}

    if target_name == "user_list":
        save_editer()
    elif target_name == "omiai_list":
        save_editer()
    else:
        print_html("kanri_saveedit_select_tmp.html", context)


def save_data(open_func, save_func, form):
    """共通のデータ保存処理."""
    original_data = open_func()  # 元のデータを取得
    updated_data = {}

    for i in range(len(original_data)):
        user_name = str(form.get(f"{i},user_name"))
        if user_name and user_name in original_data:  # ユーザー名が存在するか確認
            updated_data[user_name] = {
                v: form.get(f"{i},{v}", original_data[user_name].get(v, ""))
                for v in original_data[user_name].keys()
            }
        else:
            error(
                f"警告: インデックス {i} のユーザー名 '{user_name}' が original_data に存在しません。"
            )

    save_func(updated_data)


def save_specific_data(target_name, open_func, save_func, form):
    """target_dataに応じたデータ保存処理."""
    save_data = open_func(target_name)  # 元データを取得
    if isinstance(save_data, dict) and all(
        isinstance(v, dict) for v in save_data.values()
    ):
        # ネストされた辞書の場合（zukan_data, waza_data, room_key_data など）
        updated_data = {}
        i = 0
        while f"{i},name" in form:  # "name" フィールドが存在する限りループ
            name = form[f"{i},name"]
            # 元データのキー名を動的に取得（存在しない場合は空の辞書を使用）
            original_keys = save_data.get(name, {}).keys()
            updated_data[name] = {
                k: form.get(f"{i},{k}", save_data.get(name, {}).get(k, ""))
                for k in original_keys  # 元データのキー名を使用
            }
            # 数値変換
            for k in updated_data[name]:
                if str(updated_data[name][k]).isdecimal():
                    updated_data[name][k] = int(updated_data[name][k])
            i += 1
        save_func(updated_data, target_name)
    elif isinstance(save_data, list):
        # リスト形式の場合（party_data, park_data など）
        save_data = [
            {v: form[f"{i},{v}"] for v in save_data[i].keys()}
            for i in range(len(save_data))
        ]
        save_func(save_data, target_name)
    else:
        # 単一辞書の場合（user_data, vips_data など）
        save_data = {v: form.get(f"0,{v}", "") for v in save_data.keys()}
        save_func(save_data, target_name)


def save_edit_save():
    target_name = FORM["target_name"]
    target_data = FORM["target_data"]

    # 数値変換
    for key in FORM.keys():
        if str(FORM[key]).isdecimal():
            FORM[key] = int(FORM[key])
        else:
            FORM[key] = FORM[key]

    match target_name:
        case "user_list":
            txt = "ユーザーリストを更新しました。"
            save_data(
                open_user_list,
                save_user_list,
                FORM,
            )
        case "omiai_list":
            txt = "お見合いリストを更新しました。"
            save_data(open_omiai_list, save_omiai_list, FORM)

    match target_data:
        case "user_data":
            txt = "ユーザー情報"
            save_specific_data(target_name, open_user, save_user, FORM)
        case "vips_data":
            txt = "その他データ"
            save_specific_data(target_name, open_vips, save_vips, FORM)
        case "room_key_data":
            txt = "部屋の鍵データ"
            save_specific_data(
                target_name,
                open_room_key,
                save_room_key,
                FORM,
            )
        case "waza_data":
            txt = "習得特技データ"
            save_specific_data(target_name, open_waza, save_waza, FORM)
        case "zukan_data":
            txt = "図鑑データ"
            save_specific_data(target_name, open_zukan, save_zukan, FORM)
        case "party_data":
            txt = "パーティーデータ"
            save_specific_data(target_name, open_party, save_party, FORM)
        case "park_data":
            txt = "モンスターパークデータ"
            save_specific_data(target_name, open_park, save_park, FORM)

    result(f"{target_name}の{txt}を更新しました。")


# ================#
# dat_update     #
# ================#
def convert_dat_files():
    """datフォルダのCSVをPickleに変換"""
    try:
        files = glob.glob("./dat/*.csv")
        os.makedirs("./dat/pickle", exist_ok=True)

        def process_file(file):
            base_name = os.path.basename(file).replace(".csv", ".pickle")
            save_path = os.path.join("./dat/pickle", base_name)
            data = (
                pd.read_csv(file, encoding="utf-8_sig", index_col="name")
                .convert_dtypes()
                .fillna("")
                .sort_values("no")
                .to_dict(orient="index")
            )
            with open(save_path, mode="wb") as f:
                pickle.dump(data, f)

        with ThreadPoolExecutor(max_workers=Conf.get("max_workers", 4)) as executor:
            executor.map(process_file, files)
    except (pd.errors.ParserError, IOError) as e:
        error(f"データファイルの変換に失敗しました: {e}", "kanri")


def update_isekai_limit(M_list):
    """異世界最深部設定を更新"""
    # confファイルを書き換えるので注意！
    isekai_max_limit = max(
        [mon["階層B"] for mon in M_list.values() if (mon["room"] in ("特殊"))]
    )
    with fileinput.FileInput(
        "conf.py", inplace=True, backup=".bak", encoding="utf-8"
    ) as f:
        for line in f:
            print(
                re.sub(
                    r"Conf\[\"isekai_max_limit\"\] = \d*",
                    f'Conf["isekai_max_limit"] = {isekai_max_limit}',
                    line,
                ),
                end="",
            )


def dat_update_check(in_name, M_list, Tokugi_dat):
    """ユーザーの図鑑と技データを更新"""
    user = open_user(in_name)
    zukan = open_zukan(in_name)
    waza = open_waza(in_name)

    def update_data(new_data, existing_data, data_type, save_func):
        # 新しいデータに既存の取得状態を反映
        for name in new_data:
            if name in existing_data:
                new_data[name]["get"] = existing_data[name].get("get", 0)

        save_func(new_data, in_name)

        if data_type == "zukan":
            get = sum(v.get("get") == 1 for v in new_data.values())
            mleng = len(new_data)
            user["getm"] = f"{get}／{mleng}匹 ({get / mleng * 100:.2f}％)"
            save_user(user, in_name)

    # 図鑑の更新チェック
    new_zukan = {
        name: {"no": mon["no"], "m_type": mon["m_type"], "get": 0}
        for name, mon in M_list.items()
    }
    update_data(new_zukan, zukan, "zukan", save_zukan)

    # 技の更新チェック
    if len(Tokugi_dat) != len(waza):
        new_waza = {
            name: {"no": v["no"], "type": v["type"], "get": 0}
            for name, v in Tokugi_dat.items()
        }
        update_data(new_waza, waza, "waza", save_waza)


def dat_update():
    """データファイルを更新し、ユーザー情報を反映"""
    convert_dat_files()

    # 配合リスト2種を作り直す
    haigou_list_make.haigou_list_make()

    M_list = open_monster_dat()
    Tokugi_dat = open_tokugi_dat()

    # 異世界最深部設定
    update_isekai_limit(M_list)

    def process_user(name):
        dat_update_check(name, M_list, Tokugi_dat)

    u_list = open_user_list()
    process_batch(u_list.keys(), process_user)
    result("datファイルの更新を反映しました。")


# ================#
# cgi_python     #
# ================#
def haigou_list_make():
    # 配合リスト2種を作り直す
    haigou_list_make.haigou_list_make()

    result("配合リストHTMLを作成しました。")


# ============================================================#
def token_check():
    session = get_session()
    form_token = FORM.get("token", "")
    session_token = session.get("token", "")

    if not form_token or not secrets.compare_digest(session_token, form_token):
        # pass
        error("トークンが一致しないです", "kanri")

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


def top_level_functions(body):
    return (f for f in body if isinstance(f, ast.FunctionDef))


def parse_ast(filename):
    with open(filename, "rt", encoding="utf-8") as file:
        return ast.parse(file.read(), filename=filename)


# ============================================================#

if __name__ == "__main__":

    # フォームを辞書化
    form = cgi.FieldStorage(
        fp=sys.stdin,
        environ=os.environ,
        keep_blank_values=True,
    )

    FORM = {key: form.getvalue(key) for key in form.keys()}

    if "mode" not in FORM:
        set_session(FORM := {"token": secrets.token_hex(16)})
        OPEN_K()
    elif os.environ["REQUEST_METHOD"] != "POST":
        error("不正ですか？by管理モード", "top")

    # このファイル内の関数一覧と取得
    tree = parse_ast("kanri.py")
    func_list = [func.name for func in top_level_functions(tree.body)]

    # FORM["mode"]内に実行関数名が入ってる
    # 一覧にあれば実行
    if FORM["mode"] in func_list:
        FORM |= token_check()
        admin_check(FORM)

        func = globals().get(FORM["mode"])
        if func:
            func()
        else:
            error(f"関数 [{FORM['mode']}] が見つかりませんでした。", "top")
    else:
        error(f"無効なモード [{FORM['mode']}] です。", "top")

    error("あっれれ～？おっかしぃぞぉ～by管理モード")
