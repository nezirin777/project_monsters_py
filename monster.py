#!D:\Python\Python314\python.exe

# monster.py - トップページの処理

import cgi
import secrets
import os
import sys
from itertools import islice
from typing import Generator, Iterator

import conf
from cgi_py.tournament import tournament
from sub_def.file_ops import open_user_list, get_ranked_user_list, get_tournament_status
from sub_def.crypto import set_session, get_session
from sub_def.user_ops import (
    get_del_day,
    get_client_ip,
    run_daily_delete_check,
    is_ip_banned,
)
from sub_def.utils import print_html, error, get_and_clear_flash

Conf = conf.Conf

sys.stdout.reconfigure(encoding="utf-8")


class UserListManager:

    def __init__(self) -> None:
        ulist = open_user_list()
        # ランキング順にユーザーデータを整形
        self.u_list: dict = get_ranked_user_list(ulist)
        self.u_count: int = len(self.u_list)

    def user_mlist(self, user_data: dict) -> Iterator[dict]:
        """パーティの先頭3体をモンスター情報辞書として順に返すジェネレーター"""
        for i in range(1, 4):
            name = user_data.get(f"m{i}_name")
            if not name:
                continue
            yield {
                "name": name,
                "lv": user_data.get(f"m{i}_lv", 0),
                "hai": user_data.get(f"m{i}_hai", 0),
            }

    def create_users_list(self, start: int, end: int) -> list[dict]:
        """ランキングリストの指定範囲をテンプレート用辞書リストに変換して返す"""
        return [
            {
                "user_name": name,
                "rank": user["rank"],
                "key": user["key"],
                "money": user["money"],
                "getm": user.get("getm", 0),
                "delday": get_del_day(user["bye"]),
                "monsters": list(self.user_mlist(user)),
                "mes": user.get("mes", ""),
            }
            for name, user in islice(self.u_list.items(), start, end)
        ]


class TopPageRenderer:
    MAINTENANCE_MODE = os.path.exists("mente.mente")

    def __init__(self) -> None:
        # キャッシュ事故を防ぐため、Cookieからの in_name の強制埋め込みを廃止
        session = get_session()
        self.flash_msg, self.flash_type = get_and_clear_flash(session)

        self.token = secrets.token_hex(16)
        set_session({"token": self.token, "ref": "top"})

        status = get_tournament_status()
        self.t_time: str = status["t_time"]
        self.t_count: int = status["t_count"]

    def check_tournament(self) -> None:
        """トーナメント開催を確認（日時超過で実行）"""
        if self.t_count >= 0:
            return
        try:
            tournament()
        except Exception as e:
            error(f"トーナメント処理中にエラーが発生しました: {str(e)}", "top")

    def render(self, page: int, user_list_manager: UserListManager) -> None:
        """トップページをレンダリングして出力する"""
        self.check_tournament()

        # 開始・終了インデックスを動的に決定
        max_show = Conf.get("maxshow", 100)
        if page == 1:
            start, end = 0, max_show
        else:
            start, end = max_show, user_list_manager.u_count

        # 必要なデータを生成
        rank_text = f"RANKING [{start + 1}位～{end}位]"
        users = user_list_manager.create_users_list(start, end)

        content = {
            "Conf": Conf,
            "token": self.token,
            "maintenance": self.MAINTENANCE_MODE,
            "rank_text": rank_text,
            "users": users,
            "t_count": self.t_count,
            "t_time": self.t_time,
            "u_count": user_list_manager.u_count,
            "fol": FORM.get("fol", ""),
            "flash_msg": self.flash_msg,
            "flash_type": self.flash_type,
        }

        # URLのパラメータ(GET)で view モードが指定された場合はイベントログ画面を出す
        if FORM.get("mode", "") == "view":
            print_html("top_eventlog_tmp.html", content)
        else:
            print_html("top_tmp.html", content)


if __name__ == "__main__":
    client_ip = get_client_ip()  # クライアントIPを取得

    # IPアドレスが禁止リストに含まれている場合はアクセスを拒否
    if is_ip_banned(client_ip):
        error("あなたのIPは禁止されています", 99)

    # フォームを辞書化 (GET通信のクエリパラメータも取得可能)
    form = cgi.FieldStorage()
    FORM = {key: form.getfirst(key) for key in form}

    # パラメーターによるセーブデータフォルダ分岐処理
    conf.apply_fol(FORM)

    try:
        page = int(FORM.get("page", "1"))
        if page not in (1, 2):
            raise ValueError
    except ValueError:
        error(f"無効なページ番号です: {FORM.get('page', '1')}", "top")

    # 放置ユーザーの削除チェック（1日1回のみ実行。ロック取得失敗時は正常スキップ）
    run_daily_delete_check()

    user_list_manager = UserListManager()
    renderer = TopPageRenderer()
    renderer.render(
        page,
        user_list_manager,
    )
