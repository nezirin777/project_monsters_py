#!D:\Python\Python314\python.exe

import sys
import cgi
import os
import datetime
import shutil
import secrets
import pickle
import pandas as pd
import glob
import json
import random
import copy
from concurrent.futures import ThreadPoolExecutor, as_completed

from cgi_py import csv_to_pickle, pickle_to_csv, haigou_list_make

# import sub_def
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
    open_user,
    open_party,
    open_vips,
    open_room_key,
    open_waza,
    open_zukan,
    open_park,
    save_user,
    save_room_key,
    save_party,
    save_waza,
    save_zukan,
    save_park,
    save_vips,
)
from sub_def.monster_ops import monster_select
from sub_def.user_ops import delete_user, backup
from sub_def.utils import error, print_html
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

CSV_DEFS_MASTER = Conf.get("csv_defs_master", {})
CSV_DEFS_GLOBAL = Conf.get("csv_defs_global", {})
CSV_DEFS_USER = Conf.get("csv_defs_user", {})


# ==============#
# 	進捗状況表示 #
# ==============#
def process_batch(users, process_func, result_collector=None, batch_size=10):
    # 進捗バッチ処理
    total_users = len(users)
    progress = {"total": total_users, "completed": 0, "status": "running"}
    last_written = 0  # 最後に進捗を書き込んだ完了数
    errors = []

    with ThreadPoolExecutor(max_workers=min(6, os.cpu_count() or 4)) as executor:
        futures = {executor.submit(process_func, user): user for user in users}
        completed = 0

        for future in as_completed(futures):
            user_info = futures[future]  # 辞書全体

            try:
                result = future.result()
                if result_collector is not None and result is not None:
                    # ★★★ ここを確実に修正 ★★★
                    user_name = (
                        user_info.get("user_name")
                        if isinstance(user_info, dict)
                        else str(user_info)
                    )
                    if user_name:
                        result_collector[user_name] = result
            except Exception as e:
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
                if completed - last_written >= batch_size or completed == total_users:
                    progress["completed"] = completed
                    try:
                        with open(progress_file, mode="w", encoding="utf-8") as ff:
                            json.dump(progress, ff)
                        last_written = completed
                    except Exception as e:
                        errors.append(f"進捗ファイル書き込みエラー: {e}")

    try:
        if os.path.exists(progress_file):
            os.remove(progress_file)
    except Exception:
        pass

    return errors


# ==========#
# リザルト #
# ==========#
def result(mes=""):
    content = {
        "Conf": Conf,
        "token": FORM["token"],
        "mes": mes,
        "kanri": True,
    }

    print_html("result_tmp.html", content)


# ==================#
# confオーバーライド #
# ==================#
def update_conf_value(key, value):
    path = Conf["override_file"]

    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}

    data[key] = value

    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    os.replace(tmp, path)


# ==============#
# 	管理モード	#
# ==============#
def OPEN_K():
    print_html("kanri_login_tmp.html", {"Conf": Conf, "token": FORM["token"]})


def KANRI():
    token = FORM["token"]
    u_list = open_user_list()

    mente_chek = True if os.path.exists("mente.mente") else None

    # テンプレートに渡すデータ
    data = {"mente_chek": mente_chek, "users": u_list, "token": token, "Conf": Conf}

    print_html("kanri_tmp.html", data)


# ====================#
# メンテナンスモード   #
# ====================#
def MENTE():
    global MAINTENANCE_MODE

    mente_path = "mente.mente"

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

    update_conf_value("event_boost", val)

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

    all_data = open_user_all(target_name)
    all_data["user"]["pass"] = crypted

    save_user_all(all_data, target_name)

    u_list = open_user_list()
    if target_name in u_list:
        u_list[target_name]["pass"] = crypted
        save_user_list(u_list)

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

    delete_user(target_name)

    u_list = open_user_list()
    u_list.pop(target_name, None)
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

    def re_start_sub(user_info):
        try:
            user_name = user_info["user_name"]
            crypted = user_info.get("crypted", "")

            m_name = random.choice(monset)

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

            # user_list 用データ
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

    # ======================
    # メイン
    # ======================
    u_list = open_user_list()
    users = [
        {"user_name": name, "crypted": info.get("pass", "")}
        for name, info in u_list.items()
    ]

    new_userlist = {}

    errors = process_batch(users, re_start_sub, result_collector=new_userlist)

    save_user_list(new_userlist)
    save_omiai_list({})

    msg = "ゲームを初期化、リスタートしました。"
    if errors:
        msg += "<br><br>一部エラーが発生しました。<br>" + "<br>".join(errors)

    result(msg)


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
def FUKUGEN():
    # セーブデータフォルダ内各ユーザー名取得
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

    new_userlist = {}

    def process_user_wrapper(in_name):
        try:
            all_data = open_user_all(in_name)
            user = all_data.get("user", {})
            pt = all_data.get("party", [])
            return {
                "pass": user.get("pass", ""),
                "host": "",
                "bye": bye_day,
                "m1_name": pt[0]["name"] if pt else "",
                "m1_hai": pt[0]["hai"] if pt else 0,
                "m1_lv": pt[0]["lv"] if pt else 0,
                "m2_name": pt[1]["name"] if len(pt) > 1 else "",
                "m2_hai": pt[1]["hai"] if len(pt) > 1 else "",
                "m2_lv": pt[1]["lv"] if len(pt) > 1 else "",
                "m3_name": pt[2]["name"] if len(pt) > 2 else "",
                "m3_hai": pt[2]["hai"] if len(pt) > 2 else "",
                "m3_lv": pt[2]["lv"] if len(pt) > 2 else "",
                "key": user.get("key", 0),
                "money": user.get("money", 0),
                "getm": user.get("getm", "0／0匹(0％)"),
                "mes": user.get("mes", ""),
            }
        except Exception as e:
            return None  # エラー時はスキップ

    errors = process_batch(
        user_dirs,
        process_user_wrapper,
        result_collector=new_userlist,
    )
    save_user_list(new_userlist)

    msg = "ユーザー登録データ(user_list.pickle)を再構築しました。"
    if errors:
        msg += "<br><br>一部エラーが発生しました。<br>" + "<br>".join(errors)

    result(msg)


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
        "Conf": Conf,
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

    all_data = open_user_all(target_name)

    party = all_data.get("party", [])

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

    all_data["party"] = party
    save_user_all(all_data, target_name)

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
        all_data = open_user_all(name)
        user = all_data.get("user", {})
        user["money"] = user.get("money", 0) + money
        user["medal"] = user.get("medal", 0) + medal
        user["key"] = user.get("key", 0) + key
        all_data["user"] = user
        save_user_all(all_data, name)

    if target_name == "全員":
        u_list = open_user_list()
        errors = process_batch(list(u_list.keys()), haifu)

        msg = "全員にプレゼントを送りました。"
        if errors:
            msg += "<br><br>一部エラーが発生しました。<br>" + "<br>".join(errors)

        result(msg)

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
        "Conf": Conf,
    }

    print_html("kanri_saveedit_table_tmp.html", context)


def save_editer():
    target_name = FORM.get("target_name")
    target_data = FORM.get("target_data")

    if not target_name:
        error("対象が選択されていません。", "kanri")

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
            # 個別ユーザーデータの場合
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


def save_edit_select():
    target_name = FORM.get("target_name")
    if not target_name:
        error("対象が選択されていません。", "kanri")

    context = {"target_name": target_name, "token": FORM["token"], "Conf": Conf}

    if target_name in ("user_list", "omiai_list"):
        save_editer()
    else:
        print_html("kanri_saveedit_select_tmp.html", context)


def save_edit_save():
    target_name = FORM["target_name"]
    target_data = FORM["target_data"]

    # フォームの数値変換
    for key in list(FORM.keys()):
        try:
            FORM[key] = int(FORM[key])
        except (ValueError, TypeError):
            pass

    # user_list / omiai_list の場合（従来通り）
    if target_name == "user_list":
        txt = "ユーザーリストを更新しました。"
        original = open_user_list()
        updated = {}
        for i in range(len(original)):
            user_name = str(FORM.get(f"{i},user_name", ""))
            if user_name and user_name in original:
                updated[user_name] = {
                    k: FORM.get(f"{i},{k}", original[user_name].get(k))
                    for k in original[user_name].keys()
                }
        save_user_list(updated)
        result(txt)
        return

    if target_name == "omiai_list":
        txt = "お見合いリストを更新しました。"
        original = open_omiai_list()
        updated = {}
        for i in range(len(original)):
            user_name = str(FORM.get(f"{i},user_name", ""))
            if user_name and user_name in original:
                updated[user_name] = {
                    k: FORM.get(f"{i},{k}", original[user_name].get(k))
                    for k in original[user_name].keys()
                }
        save_omiai_list(updated)
        result(txt)
        return

    # 個別ユーザーデータの場合（新型式対応）
    all_data = open_user_all(target_name)

    match target_data:
        case "user_data":
            txt = "ユーザー情報"
            user = all_data.get("user", {})
            for k in list(user.keys()):
                user[k] = FORM.get(f"0,{k}", user.get(k))
            all_data["user"] = user

        case "vips_data":
            txt = "その他データ"
            vips = all_data.get("vips", {})
            for k in list(vips.keys()):
                vips[k] = FORM.get(f"0,{k}", vips.get(k))
            all_data["vips"] = vips

        case "room_key_data":
            txt = "部屋の鍵データ"
            room_key = {}
            i = 0
            while f"{i},name" in FORM:
                name = FORM[f"{i},name"]
                if name:
                    room_key[name] = {
                        k: FORM.get(
                            f"{i},{k}",
                            all_data.get("room_key", {}).get(name, {}).get(k),
                        )
                        for k in all_data.get("room_key", {}).get(name, {})
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
                    waza[name] = {
                        k: FORM.get(
                            f"{i},{k}", all_data.get("waza", {}).get(name, {}).get(k)
                        )
                        for k in all_data.get("waza", {}).get(name, {})
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
                    zukan[name] = {
                        k: FORM.get(
                            f"{i},{k}", all_data.get("zukan", {}).get(name, {}).get(k)
                        )
                        for k in all_data.get("zukan", {}).get(name, {})
                    }
                i += 1
            all_data["zukan"] = zukan

        case "party_data":
            txt = "パーティーデータ"
            party = all_data.get("party", [])
            for i in range(len(party)):
                for k in list(party[i].keys()):
                    party[i][k] = FORM.get(f"{i},{k}", party[i].get(k))
            all_data["party"] = party

        case "park_data":
            txt = "モンスターパークデータ"
            park = all_data.get("park", [])
            for i in range(len(park)):
                for k in list(park[i].keys()):
                    park[i][k] = FORM.get(f"{i},{k}", park[i].get(k))
            all_data["park"] = park

        case _:
            error("不明なtarget_dataです", "kanri")

    # 一括保存
    save_user_all(all_data, target_name)

    result(f"{target_name}の{txt}を更新しました。")


# ================#
# dat_update     #
# ================#
def update_isekai_limit(M_list):
    """異世界最深部設定を更新"""
    # confオーバーライドファイルに異世界最深部の最大階層を保存
    isekai_max_limit = max(
        [mon["階層B"] for mon in M_list.values() if (mon["room"] in ("異世界"))]
    )

    update_conf_value("isekai_max_limit", isekai_max_limit)


def dat_update_check(in_name, M_list, Tokugi_dat):
    """ユーザーの図鑑と技データを更新"""
    all_data = open_user_all(in_name)
    user = all_data.get("user", {})
    zukan = all_data.get("zukan", {})
    waza = all_data.get("waza", {})

    # 図鑑更新
    new_zukan = {
        name: {
            "no": mon["no"],
            "m_type": mon["m_type"],
            "get": zukan.get(name, {}).get("get", 0),
        }
        for name, mon in M_list.items()
    }
    all_data["zukan"] = new_zukan

    # 技更新
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

    # getm 更新
    get = sum(v.get("get") == 1 for v in new_zukan.values())
    mleng = len(new_zukan)
    user["getm"] = (
        f"{get}／{mleng}匹 ({get / mleng * 100:.2f}％)" if mleng > 0 else "0／0匹(0％)"
    )

    save_user_all(all_data, in_name)


def dat_update():
    """データファイルを更新し、ユーザー情報を反映"""
    for csv_name, conf_def in CSV_DEFS_MASTER.items():
        csv_to_pickle.convert_csv_to_pickle(csv_name)

    # 配合リスト2種を作り直す
    haigou_list_make.haigou_list_make()

    M_list = open_monster_dat()
    Tokugi_dat = open_tokugi_dat()

    # 異世界最深部設定
    update_isekai_limit(M_list)

    def process_user(name):
        dat_update_check(name, M_list, Tokugi_dat)

    u_list = open_user_list()
    errors = process_batch(u_list.keys(), process_user)

    msg = "datファイルの更新を反映しました。"
    if errors:
        msg += "<br><br>一部エラーが発生しました。<br>" + "<br>".join(errors)

    result(msg)


# ================#
# cgi_python     #
# ================#
def make_haigou_list():
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


FUNCTION_MAP = {
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
        set_session(FORM := {"token": secrets.token_hex(16)})
        OPEN_K()

    if os.environ["REQUEST_METHOD"] != "POST":
        error("不正ですか？by管理モード", "top")

    func = FUNCTION_MAP.get(FORM["mode"])
    if not func:
        error(f"無効なモード [{FORM['mode']}] です。", "top")

    FORM |= token_check()
    admin_check(FORM)
    func()

    error("あっれれ～？おっかしぃぞぉ～by管理モード")
