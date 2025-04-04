# user_ops.py

import sys
import os

import datetime
import socket  # host取得
import shutil  # ファイル操作
import re

import conf

from .file_ops import open_omiai_list, save_omiai_list, open_user_list, save_user_list
from .utils import error

sys.stdout.reconfigure(encoding="utf-8")
sys.stdin.reconfigure(encoding="utf-8")
Conf = conf.Conf

compiled_noip = [re.compile(ip) for ip in conf.noip]


# ==============#
# バックアップ #
# ==============#
def backup():
    if Conf["backup"] == 1:
        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S")
            backup_path = os.path.join(Conf["backfolder"], timestamp)

            # バックアップ先ディレクトリを作成
            os.makedirs(backup_path, exist_ok=True)

            # save ディレクトリ全体を再帰的にコピー
            shutil.copytree(Conf["savedir"], backup_path, dirs_exist_ok=True)

        except FileNotFoundError as e:
            error(f"バックアップ元ディレクトリが見つかりません: {e}")
        except PermissionError as e:
            error(f"バックアップ作成時の権限エラー: {e}")
        except OSError as e:
            error(f"バックアップ作成時のOSエラー: {e}")


# =============#
# 削除時間取得 #
# =============#
def getdelday(bye):
    return (
        datetime.datetime.strptime(str(bye), "%Y-%m-%d") - datetime.datetime.now()
    ).days


# ================#
# 	保存期間調査  #
# ================#
def delete_user(target):
    """
    指定されたユーザーを削除し、お見合いリストから該当データを更新・削除。
    """
    try:
        # お見合い登録データから対象ユーザー削除
        omiai_list = open_omiai_list()
        if target in omiai_list:
            del omiai_list[target]

        # 対象ユーザーにお見合い申請しているユーザーのデータを更新
        for name, opt in omiai_list.items():
            if opt.get("request") == target:
                opt.update(
                    {
                        "request": "",
                        "cancel": f"{target}さんへの依頼はお断りされてしまったようです・・・",
                    }
                )
        save_omiai_list(omiai_list)

        # ユーザーディレクトリを削除
        user_dir = os.path.join(Conf["savedir"], target)
        if os.path.exists(user_dir):
            shutil.rmtree(user_dir)
        else:
            error(f"ユーザーディレクトリが見つかりません: {user_dir}", 99)

    except OSError as e:
        error(f"ユーザーディレクトリの削除中にエラーが発生しました: {e}", 99)


def delete_check():
    """
    ユーザーリストを確認し、削除対象のユーザーを削除。
    """
    u_list = open_user_list()
    for key in list(u_list.keys()):  # ループ中の辞書変更対策でlist()を使用
        if getdelday(u_list[key]["bye"]) <= 0:
            delete_user(key)
            del u_list[key]
    save_user_list(u_list)


# ==========#
# host取得 #
# ==========#
def get_client_ip():
    """
    クライアントのIPアドレスを取得します。
    X-Forwarded-Forヘッダーを考慮して、最も信頼できるIPアドレスを返します。
    """
    try:
        # 環境変数からIPアドレスを取得
        x_forwarded_for = os.environ.get("HTTP_X_FORWARDED_FOR", "")
        remote_addr = os.environ.get("REMOTE_ADDR", "0.0.0.0")
        # X-Forwarded-Forが存在する場合、最初のIPを使用
        return x_forwarded_for.split(",")[0].strip() if x_forwarded_for else remote_addr
    except Exception as e:
        return "0.0.0.0"


def get_host():
    """
    クライアントのリモートアドレスからホスト名を取得する。
    - X-Forwarded-For ヘッダーを優先的に確認する。
    - ホスト名が見つからない場合はIPアドレスを返す。
    """
    ip_address = get_client_ip()
    try:
        # IPアドレスからホスト名を取得
        return socket.gethostbyaddr(ip_address)[0]
    except (socket.herror, KeyError) as e:
        return ip_address  # ホスト名解決失敗時はIPを返す
    except Exception as e:
        return ip_address


def is_ip_banned(ip_address):
    """
    指定されたIPアドレスが禁止リストに含まれているかを確認します。
    - conf.noipに設定されている禁止IPリストを正規表現でチェック。
    """
    try:
        return any(pattern.match(ip_address) for pattern in compiled_noip)
    except Exception as e:
        error(f"IP禁止チェックエラー: {e}")
        return True  # 安全側に倒す
