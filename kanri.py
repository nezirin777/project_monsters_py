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

import sub_def
import register
import conf
import cgi_py


Conf = conf.Conf
datadir = Conf["savedir"]
progress_file = os.path.join(datadir, "progress.json")

sys.stdout.reconfigure(encoding="utf-8")
# 自動でutf-8にエンコードされて出力される


# ==============#
# 	json削除	#
# ==============#
def delete_progress_file():
    """進捗ファイルを削除"""
    try:
        if os.path.exists(progress_file):
            os.remove(progress_file)
    except Exception as e:
        sub_def.error(f"進捗ファイルの削除に失敗しました: {e}")


# ==============#
# 	チェック	#
# ==============#
def admin_check():
    in_m_name = FORM["m_name"]
    in_m_pass = FORM["m_password"]

    if in_m_name == "":
        sub_def.error("MASTER_NAMEが有りません", "kanri")
    if in_m_pass == "":
        sub_def.error("MASTER_PASSWORDが有りません", "kanri")
    if in_m_name != Conf["master_name"]:
        sub_def.error("MASTER_NAMEが違います", "kanri")
    if in_m_pass != Conf["master_password"]:
        sub_def.error("MASTER_PASSWORDが違います", "kanri")

    return


# ==========#
# リザルト #
# ==========#
def result(txt=""):
    sub_def.result(txt, kanri=True, token=FORM["token"])


# ==============#
# 	管理モード	#
# ==============#
def OPEN_K():
    sub_def.print_html("kanri_login_tmp.html", {"token": FORM["token"]})


def KANRI():
    token = FORM["token"]
    u_list = sub_def.open_user_list()

    mente_chek = True if os.path.exists("mente.mente") else None

    # テンプレートに渡すデータ
    data = {
        "mente_chek": mente_chek,
        "users": u_list,
        "token": token,
    }

    sub_def.print_html("kanri_tmp.html", data)


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

    result(txt)


# =========#
# 強制登録 #
# =========#
def NEW():
    register.sinki(FORM["make_name"], FORM["make_password"], True)


# ================#
# パスワード変更  #
# ================#
def NEWPASS():
    target_name = FORM.get("target_name")
    newpass = FORM.get("newpass")

    if not (target_name):
        sub_def.error("対象ユーザーが選択されていません。", "kanri")
    if not (newpass):
        sub_def.error("新しいパスワードが入力されていません。", "kanri")

    crypted = sub_def.hash_password(newpass)
    u_list = sub_def.open_user_list()
    user = sub_def.open_user(target_name)

    user["pass"] = crypted
    u_list[target_name]["pass"] = crypted

    sub_def.save_user_list(u_list)
    sub_def.save_user(user, target_name)

    result(f"管理モードで<span>{target_name}</span>のパスワードを変更しました")


# =============#
# ユーザー削除 #
# =============#
def DEL():
    target_name = FORM.get("target_name")

    if FORM.get("Del_ck") != "on":
        sub_def.error("確認チェックがONになっていません。", "kanri")
    if not (target_name):
        sub_def.error("対象ユーザーが選択されていません。", "kanri")

    u_list = sub_def.open_user_list()

    sub_def.delete_user(target_name)
    del u_list[target_name]

    sub_def.save_user_list(u_list)

    result(f"<span>{target_name}</span>を管理モードで強制削除しました")


# =================#
# saveフォルダ削除 #
# =================#
def data_del():
    sub_def.backup()

    shutil.rmtree(datadir)
    os.makedirs(datadir)

    with open(datadir + "/tournament.log", mode="w", encoding="utf-8") as f:
        f.write(
            """<div class="medal_battle_title">まだ大会は一度も開かれていません</div><br><br><br>"""
        )

    with open(datadir + "/bbslog.log", mode="w", encoding="utf-8_sig") as f:
        f.write("")

    sub_def.open_user_list()
    sub_def.open_omiai_list()


# ===========#
# リスタート #
# ===========#
def RESTART():
    if FORM.get("Reset_ck") != "on":
        sub_def.error("確認チェックがONになっていません。", "kanri")

    new_userlist = {}
    byeday = (
        datetime.datetime.now() + datetime.timedelta(days=Conf["goodbye"])
    ).strftime("%Y-%m-%d")

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

    default_key = {
        k: {"no": v["no"], "get": 0} for k, v in sub_def.open_key_dat().items()
    }

    Tokugi_dat = sub_def.open_tokugi_dat()
    default_waza = {
        name: {"no": v["no"], "type": v["type"], "get": 0}
        for name, v in Tokugi_dat.items()
    }
    default_waza["通常攻撃"]["get"] = 1
    default_zukan = {
        k: {"no": v["no"], "m_type": v["m_type"], "get": 0}
        for k, v in sub_def.open_monster_dat().items()
    }

    u_list = sub_def.open_user_list()
    users = [{"user_name": name, "crypted": v["pass"]} for name, v in u_list.items()]

    def process_user(u):
        try:
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
            sub_def.save_user(
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
                u["user_name"],
            )

            # 追加データの初期化
            sub_def.save_room_key(default_key, u["user_name"])
            sub_def.save_waza(default_waza, u["user_name"])
            sub_def.save_zukan(default_zukan, u["user_name"])
            sub_def.save_vips({"パーク": 0}, u["user_name"])
            sub_def.save_park([], u["user_name"])

        except Exception as e:
            sub_def.error(f"ユーザー {u['user_name']} の処理中にエラー: {e}")
            sys.stdout.flush()
            return False

    total_users = len(u_list)  # 全体のユーザー数
    # 初期化
    progress = {"total": total_users, "completed": 0, "status": "running"}
    with open(progress_file, mode="w", encoding="utf-8") as ff:
        json.dump(progress, ff)

    completed = 0
    # スレッドプールを使用して並列実行
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(process_user, u): u for u in users}
        for future in as_completed(futures):
            future.result()  # 例外があればここで捕捉
            completed += 1
            if completed % 10 == 0 or completed == total_users:
                progress["completed"] = completed
                with open(progress_file, mode="w", encoding="utf-8") as ff:
                    json.dump(progress, ff)

    sub_def.save_user_list(new_userlist)
    sub_def.save_omiai_list({})
    result("ゲームを初期化、リスタートしました。")

    delete_progress_file()


# =======#
# 初期化 #
# =======#
def ALLDEL():
    if FORM["Reset_ck"] != "on":
        sub_def.error("確認チェックがONになっていません。", "kanri")

    data_del()

    result("全データを削除しました。")


# ====================#
# ユーザーデータ再構築 #
# user_list.pickle    #
# ====================#
def process_user(in_name, bye_day):
    """1ユーザー分のデータを処理する関数"""
    user = sub_def.open_user(in_name)
    pt = sub_def.open_party(in_name)
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
    completed = 0

    # 並列処理の実行
    with ThreadPoolExecutor() as executor:
        future_to_user = {
            executor.submit(process_user, in_name, bye_day): in_name
            for in_name in files_dir
        }
        for future in as_completed(future_to_user):
            in_name = future_to_user[future]
            try:
                u_list[in_name] = future.result()
                completed += 1

                # 一定間隔で進捗更新
                if completed % 10 == 0 or completed == total_users:
                    progress["completed"] = completed
                    with open(progress_file, mode="w", encoding="utf-8") as ff:
                        json.dump(progress, ff)
            except Exception as e:
                sub_def.error(f"ユーザー {in_name} の処理中にエラー: {e}", 99)

    delete_progress_file()
    sub_def.save_user_list(u_list)

    result("ユーザー登録データ(user_list.pickle)を再構築しました。")


# ====================#
# モンスター配布      #
# ====================#
def MON_PRESENT():
    target_name = FORM.get("target_name", "")

    if target_name == "":
        sub_def.error("対象ユーザーが選択されていません。", "kanri")

    M_list = sub_def.open_monster_dat()
    txt = "".join(
        [f"""<option value={name}>{name}</option>\n""" for name in M_list.keys()]
    )

    context = {
        "target_name": target_name,
        "txt": txt,
        "token": FORM["token"],
    }

    sub_def.print_html("kanri_mon_present_tmp.html", context)


# ====================#
# モンスター配布 処理 #
# ====================#
def MON_PRESENT_OK():
    target_name = FORM["target_name"]
    Mons_name = FORM.get("Mons_name")
    sex = FORM.get("sex")
    max_level = int(FORM.get("max_level", 0))
    haigou = int(FORM.get("haigou", 0))

    if not (Mons_name):
        sub_def.error("モンスターを選択してください", "kanri")
    if not (sex):
        sub_def.error("性別を選択してください", "kanri")
    if not (max_level):
        sub_def.error("MAXレベルを入力してください", "kanri")
    if not (haigou):
        sub_def.error("配合回数を入力してください", "kanri")

    party = sub_def.open_party(target_name)

    if len(party) >= 10:
        sub_def.error("パーティがいっぱいで追加することができません。", "kanri")

    new_mob = sub_def.monster_select(Mons_name, haigou)
    new_mob["lv"] = 1
    new_mob["mlv"] = max_level
    new_mob["sex"] = sex
    new_mob["hai"] = haigou

    party.append(new_mob)
    for i, pt in enumerate(party, 1):
        pt["no"] = i

    sub_def.save_party(party, target_name)

    result(f"{target_name}へモンスターを配布しました")


# ====================#
# プレゼント          #
# ====================#
def PRESENT():
    target_name = FORM.get("target_name", "")

    try:
        money = int(FORM.get("money", 0))
        medal = int(FORM.get("medal", 0))
        key = int(FORM.get("key", 0))
    except ValueError:
        sub_def.error("お金、メダル、キーは整数で入力してください。", "kanri")

    if target_name == "":
        sub_def.error("ユーザーが選択されていません。", "kanri")

    def haifu(name):
        user = sub_def.open_user(name)
        user["money"] += int(money)
        user["medal"] += int(medal)
        user["key"] += int(key)
        sub_def.save_user(user, name)

    if target_name == "全員":
        u_list = sub_def.open_user_list()
        total_users = len(u_list)  # 全体のユーザー数

        # 初期化
        progress = {"total": total_users, "completed": 0, "status": "running"}
        with open(progress_file, mode="w", encoding="utf-8") as ff:
            json.dump(progress, ff)

        batch_size = 10
        completed = 0
        # 並列処理を実行
        with ThreadPoolExecutor(max_workers=8) as executor:
            future_to_user = {
                executor.submit(haifu, name): name for name in u_list.keys()
            }
            for future in as_completed(future_to_user):
                name = future_to_user[future]
                try:
                    future.result()  # エラーがあればここでキャッチされる
                except Exception as exc:
                    sub_def.error(
                        f"ユーザー {name} の処理中にエラーが発生しました: {exc}"
                    )

                completed += 1
                if completed % batch_size == 0 or completed == total_users:
                    progress["completed"] = completed
                    with open(progress_file, mode="w", encoding="utf-8") as ff:
                        json.dump(progress, ff)

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
        sub_def.error("対象が選択されていません。", "kanri")

    cgi_py.csv_to_pickle.csv_to_pickle(target_name)

    result(f"{target_name}のcsv→pickle変換が完了しました。")


# ====================#
# pickle → csv       #
# ====================#
def pickle_to():
    target_name = FORM.get("target_name")

    if not (target_name):
        sub_def.error("対象が選択されていません。", "kanri")

    sub_def.backup()
    cgi_py.pickle_to_csv.pickle_to_csv(target_name)

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

    headers = list(rows[0].keys())

    context = {
        "txt": txt,
        "headers": headers,
        "rows": rows,
        "no_edit": no_edit,
        "target_name": target_name,
        "target_data": target_data,
        "token": FORM["token"],
    }

    sub_def.print_html("kanri_saveedit_table_tmp.html", context)


def save_editer():
    target_name = FORM.get("target_name")
    target_data = FORM.get("target_data")

    if not (target_name):
        sub_def.error("対象が選択されていません。", "kanri")

    match target_name:
        case "user_list":
            save_data = sub_def.open_user_list()
            if not (save_data):
                sub_def.error(
                    "現在登録者はいないようです。<br>編集できません。", "kanri"
                )
            save_data = [{"user_name": u} | v for u, v in save_data.items()]
            txt = "登録ユーザーリスト"
        case "omiai_list":
            save_data = sub_def.open_omiai_list()
            if not (save_data):
                sub_def.error(
                    "現在お見合い登録者はいないようです。<br>編集できません。", "kanri"
                )
            save_data = [{"user_name": u} | v for u, v in save_data.items()]
            txt = "お見合いリスト"

    match target_data:
        case "user_data":
            save_data = sub_def.open_user(target_name)
            txt = "ユーザー情報"
        case "party_data":
            save_data = sub_def.open_party(target_name)
            txt = "パーティーデータ"
        case "room_key_data":
            save_data = sub_def.open_room_key(target_name)
            save_data = [{"name": u} | v for u, v in save_data.items()]
            txt = "部屋の鍵データ"
        case "waza_data":
            save_data = sub_def.open_waza(target_name)
            save_data = [{"name": u} | v for u, v in save_data.items()]
            txt = "習得特技データ"
        case "zukan_data":
            save_data = sub_def.open_zukan(target_name)
            save_data = [{"name": u} | v for u, v in save_data.items()]
            txt = "図鑑データ"
        case "park_data":
            save_data = sub_def.open_park(target_name)
            txt = "モンスターパークデータ"
            if not (save_data):
                sub_def.error(
                    "現在パーク内にモンスターはいないようです。<br>編集できません。",
                    "kanri",
                )
        case "vips_data":
            save_data = sub_def.open_vips(target_name)
            txt = "その他データ"

    if type(save_data) == list:
        make_table(save_data, txt)
    else:
        make_table([save_data], txt)


def save_edit_select():
    target_name = FORM.get("target_name")

    if not (target_name):
        sub_def.error("対象が選択されていません。", "kanri")

    context = {"target_name": target_name, "token": FORM["token"]}

    if target_name == "user_list":
        save_editer()
    elif target_name == "omiai_list":
        save_editer()
    else:
        sub_def.print_html("kanri_saveedit_select_tmp.html", context)


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
            sub_def.error(
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
            save_data(sub_def.open_user_list, sub_def.save_user_list, FORM)
        case "omiai_list":
            txt = "お見合いリストを更新しました。"
            save_data(sub_def.open_omiai_list, sub_def.save_omiai_list, FORM)

    match target_data:
        case "user_data":
            txt = "ユーザー情報"
            save_specific_data(target_name, sub_def.open_user, sub_def.save_user, FORM)
        case "vips_data":
            txt = "その他データ"
            save_specific_data(target_name, sub_def.open_vips, sub_def.save_vips, FORM)
        case "room_key_data":
            txt = "部屋の鍵データ"
            save_specific_data(
                target_name, sub_def.open_room_key, sub_def.save_room_key, FORM
            )
        case "waza_data":
            txt = "習得特技データ"
            save_specific_data(target_name, sub_def.open_waza, sub_def.save_waza, FORM)
        case "zukan_data":
            txt = "図鑑データ"
            save_specific_data(
                target_name, sub_def.open_zukan, sub_def.save_zukan, FORM
            )
        case "party_data":
            txt = "パーティーデータ"
            save_specific_data(
                target_name, sub_def.open_party, sub_def.save_party, FORM
            )
        case "park_data":
            txt = "モンスターパークデータ"
            save_specific_data(target_name, sub_def.open_park, sub_def.save_park, FORM)

    result(f"{target_name}の{txt}を更新しました。")


# ================#
# dat_update     #
# ================#
def dat_update_check(in_name, M_list, Tokugi_dat):

    user = sub_def.open_user(in_name)
    zukan = sub_def.open_zukan(in_name)
    waza = sub_def.open_waza(in_name)

    def update_data(new_data, existing_data, data_type, save_func):
        # 新しいデータに既存の取得状態を反映
        for name in new_data.keys():
            if name in existing_data:
                new_data[name]["get"] = existing_data[name].get("get", 0)

        # データを保存
        save_func(new_data, in_name)

        # ユーザーの収集率を更新（図鑑データの場合のみ）
        if data_type == "zukan":
            get = sum(v.get("get") == 1 for v in new_data.values())
            mleng = len(new_data)
            s = get / mleng * 100
            user["getm"] = f"{get}／{mleng}匹 ({s:.2f}％)"
            sub_def.save_user(user, in_name)

    # 図鑑の更新チェック
    new_zukan = {
        name: {"no": mon["no"], "m_type": mon["m_type"], "get": 0}
        for name, mon in M_list.items()
    }
    update_data(new_zukan, zukan, "zukan", sub_def.save_zukan)

    # 技の更新チェック
    if len(Tokugi_dat) != len(waza):
        new_waza = {
            name: {"no": v["no"], "type": v["type"], "get": 0}
            for name, v in Tokugi_dat.items()
        }
        update_data(new_waza, waza, "waza", sub_def.save_waza)

    return


def dat_file():

    def pickle_dump(obj, path):
        with open(path, mode="wb") as f:
            pickle.dump(obj, f)

    def open_dat(file):
        return (
            pd.read_csv(file, encoding="utf-8_sig", index_col="name")
            .convert_dtypes()
            .fillna("")
            .sort_values("no")
            .to_dict(orient="index")
        )

    files = glob.glob("./dat/*.csv")
    os.makedirs("./dat/pickle", exist_ok=True)

    def process_file(file):
        base_name = os.path.basename(file).replace(".csv", ".pickle")
        save_path = os.path.join("./dat/pickle", base_name)
        data = open_dat(file)
        if data:
            pickle_dump(data, save_path)

    # 並列処理
    with ThreadPoolExecutor(max_workers=4) as executor:
        executor.map(process_file, files)


def dat_update():

    dat_file()

    # 配合リスト2種を作り直す
    cgi_py.haigou_list_make.haigou_list_make()

    M_list = sub_def.open_monster_dat()
    Tokugi_dat = sub_def.open_tokugi_dat()

    # 異世界最深部設定
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

    def process_user(name):
        dat_update_check(name, M_list, Tokugi_dat)

    u_list = sub_def.open_user_list()
    total_users = len(u_list)  # 全体のユーザー数

    # 初期化
    progress = {"total": total_users, "completed": 0, "status": "running"}
    with open(progress_file, mode="w", encoding="utf-8") as ff:
        json.dump(progress, ff)

    batch_size = 10
    completed = 0

    # 並列処理（ThreadPoolExecutorを使用）
    with ThreadPoolExecutor(max_workers=8) as executor:
        future_to_user = {
            executor.submit(process_user, name): name for name in u_list.keys()
        }
        for future in as_completed(future_to_user):
            name = future_to_user[future]
            try:
                future.result()  # エラーが発生した場合ここで例外がスローされる
            except Exception as exc:
                print(f"ユーザー {name} の処理中にエラーが発生しました: {exc}")

            completed += 1
            if completed % batch_size == 0 or completed == total_users:
                progress["completed"] = completed
                with open(progress_file, mode="w", encoding="utf-8") as ff:
                    json.dump(progress, ff)

    delete_progress_file()
    result("datファイルの更新を反映しました。")


# ================#
# cgi_python     #
# ================#
def cgi_python():
    dat_file()
    cgi_py.cgi_python.cgi_python()

    result("python環境へデータ変換しました。")


# ================#
# cgi_python     #
# ================#
def haigou_list_make():
    # 配合リスト2種を作り直す
    cgi_py.haigou_list_make.haigou_list_make()

    result("配合リストHTMLを作成しました。")


# ============================================================#
def token_check():
    session = sub_def.get_session()

    if FORM.get("token"):
        if not (secrets.compare_digest(session["token"], FORM["token"])):
            sub_def.error(f"トークンが一致しないです？", "kanri")
            # pass
    else:
        # pass
        sub_def.error(
            "トークンが送信されてないです？<br>繰り返し表示される場合は管理人へ連絡を。",
            "kanri",
        )

    token = secrets.token_hex(16)
    data = {
        "token": token,
        "m_name": FORM.get("m_name", session.get("m_name", "")),
        "m_password": FORM.get("m_password", session.get("m_password", "")),
    }

    session |= data
    sub_def.set_session(session)

    return session


def top_level_functions(body):
    return (f for f in body if isinstance(f, ast.FunctionDef))


def parse_ast(filename):
    with open(filename, "rt", encoding="utf-8") as file:
        return ast.parse(file.read(), filename=filename)


# ============================================================#

if __name__ == "__main__":

    # フォームを辞書化
    form = cgi.FieldStorage()
    FORM = {key: form.getvalue(key) for key in form.keys()}

    if "mode" not in FORM:
        sub_def.set_session(FORM := {"token": secrets.token_hex(16)})
        OPEN_K()
    elif os.environ["REQUEST_METHOD"] != "POST":
        sub_def.error("不正ですか？by管理モード", "top")

    # このファイル内の関数一覧と取得
    tree = parse_ast("kanri.py")
    func_list = [func.name for func in top_level_functions(tree.body)]

    # FORM["mode"]内に実行関数名が入ってる
    # 一覧にあれば実行
    if FORM["mode"] in func_list:
        FORM |= token_check()
        admin_check()
        func = globals().get(FORM["mode"])
        if func:
            func()
        else:
            sub_def.error(f"関数 [{FORM['mode']}] が見つかりませんでした。", "top")
    else:
        sub_def.error(f"無効なモード [{FORM['mode']}] です。", "top")

    sub_def.error("あっれれ～？おっかしぃぞぉ～by管理モード")
