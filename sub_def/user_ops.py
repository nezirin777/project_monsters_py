# user_ops.py

import os
import re
import shutil
import socket
import datetime
import logging

import conf

from .file_ops import (
    open_omiai_list,
    save_omiai_list,
    open_user_list,
    save_user_list,
    get_shared_lock,
    log,
)
from .utils import error

# sys.stdout.reconfigure はライブラリモジュールには不要。
# CGI エントリポイント（login.py / monster.py 等）で設定済みのため削除。

Conf = conf.Conf

# 存在しないキーによる KeyError を防ぐため get() で安全に取得する
compiled_noip: list[re.Pattern] = [re.compile(ip) for ip in Conf.get("noip", [])]


# ==============#
# バックアップ  #
# ==============#
def backup() -> None:
    """save ディレクトリ全体をタイムスタンプ付きフォルダにコピーする"""
    if not Conf["backup"]:
        return

    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S")
        backup_path = os.path.join(Conf["backfolder"], timestamp)
        os.makedirs(backup_path, exist_ok=True)
        shutil.copytree(Conf["savedir"], backup_path, dirs_exist_ok=True)

    except FileNotFoundError as e:
        error(f"バックアップ元ディレクトリが見つかりません: {e}")
    except PermissionError as e:
        error(f"バックアップ作成時の権限エラー: {e}")
    except OSError as e:
        error(f"バックアップ作成時のOSエラー: {e}")


# ==============#
# 削除時間取得  #
# ==============#
def get_del_day(bye: str) -> int:
    """
    ユーザーの削除までの残り日数を返す。
    日付フォーマットが不正な場合は 0 を返す（即削除対象にしない安全側の挙動）。
    """
    try:
        return (
            datetime.datetime.strptime(str(bye), "%Y-%m-%d") - datetime.datetime.now()
        ).days
    except ValueError:
        logging.warning(f"get_del_day: 不正な日付フォーマット '{bye}'")
        return 0


# ================#
# 保存期間チェック #
# ================#
def run_daily_delete_check() -> None:
    """
    放置ユーザーの削除チェックを 1 日 1 回だけ実行する。
    別プロセスがすでに実行中の場合はロック取得に失敗するため、
    重複実行を避けて静かにスキップする（エラーではない）。
    """
    marker_path = os.path.join(Conf["savedir"], "last_delete_check.txt")
    today = datetime.date.today().isoformat()

    lock = get_shared_lock("delete_check")

    if not lock.lock():
        # 別プロセスが実行中 → 重複実行を避けるため正常スキップ
        return

    try:
        if os.path.exists(marker_path):
            with open(marker_path, encoding="utf-8") as f:
                last_run = f.read().strip()
            if last_run == today:
                return  # 本日分は実行済み

        delete_check()

        with open(marker_path, "w", encoding="utf-8") as f:
            f.write(today)

    except OSError as e:
        error(f"削除チェックの実行記録更新に失敗しました: {e}", 99)
    finally:
        lock.unlock()


def delete_user(target: str) -> None:
    """
    指定ユーザーを削除し、お見合いリストから関連データを更新する。

    Note:
        ユーザーディレクトリが存在しない場合は警告ログを出力して続行する。
        delete_check() のループ中に呼ばれるケースでは、1 件の欠損で
        全体処理を止めないようにするため error() は使わない。
    """
    try:
        # お見合いリストから対象ユーザーを削除
        omiai_list = open_omiai_list()
        if target in omiai_list:
            del omiai_list[target]

        # 対象ユーザーにお見合いを申請中の相手のステータスを更新
        for name, opt in omiai_list.items():
            if opt.get("request") == target:
                opt.update(
                    {
                        "request": "",
                        "cancel": f"{target}さんへの依頼はお断りされてしまったようです・・・",
                    }
                )
        save_omiai_list(omiai_list)

        user_dir = os.path.join(Conf["savedir"], target)
        if os.path.exists(user_dir):
            shutil.rmtree(user_dir)
        else:
            # 部分削除済み等の理由でディレクトリが消えている場合は警告のみ
            log(f"[WARN] delete_user: ディレクトリが見つかりません: {user_dir}")

    except OSError as e:
        error(f"ユーザーディレクトリの削除中にエラーが発生しました: {e}", 99)


def delete_check() -> None:
    """
    ユーザーリストを走査し、保存期限切れのユーザーを削除する。
    ループ中にリストを変更するため、キーのコピーに対してイテレートする。
    """
    u_list = open_user_list()
    for key in list(u_list.keys()):
        if get_del_day(u_list[key]["bye"]) <= 0:
            delete_user(key)
            del u_list[key]
    save_user_list(u_list)


# ============#
# IP 関連    #
# ============#
def get_client_ip() -> str:
    """
    クライアントの IP アドレスを返す。
    リバースプロキシ経由の場合は X-Forwarded-For ヘッダーを優先する。
    """
    try:
        x_forwarded_for = os.environ.get("HTTP_X_FORWARDED_FOR", "")
        remote_addr = os.environ.get("REMOTE_ADDR", "0.0.0.0")
        return x_forwarded_for.split(",")[0].strip() if x_forwarded_for else remote_addr
    except Exception:
        return "0.0.0.0"


def get_host() -> str:
    """
    クライアント IP から逆引きでホスト名を取得する。
    解決できない場合は IP アドレスをそのまま返す。

    Note:
        gethostbyaddr() は DNS 逆引きを行うため、環境によって数百 ms の
        レイテンシが発生することがある。
    """
    ip_address = get_client_ip()
    try:
        return socket.gethostbyaddr(ip_address)[0]
    except (socket.herror, KeyError):
        return ip_address
    except Exception:
        return ip_address


def is_ip_banned(ip_address: str) -> bool:
    """
    IP アドレスが禁止リストに含まれているか判定する。
    判定中に例外が発生した場合は安全側（True = 禁止）として扱い、
    リクエスト全体をクラッシュさせない。
    """
    try:
        return any(pattern.match(ip_address) for pattern in compiled_noip)
    except Exception as e:
        # 正規表現マッチのエラーでリクエストを止めるのは過剰なため、
        # 警告ログだけ出して安全側（アクセス拒否）を返す
        logging.warning(f"IP禁止チェック中に例外が発生しました: {e}")
        return True
