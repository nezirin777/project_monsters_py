#!D:\Python\Python312\python.exe

import cgi
import secrets
import os
from itertools import islice

import conf
from cgi_py.tournament import tournament
from sub_def.file_ops import open_user_list, get_tournament_status
from sub_def.crypto import get_cookie, set_session
from sub_def.user_ops import getdelday, get_client_ip, delete_check, is_ip_banned
from sub_def.utils import print_html, error


Conf = conf.Conf


class UserListManager:

    def __init__(self):
        self.u_list = open_user_list()
        self.u_count = len(self.u_list)

    def user_mlist(self, user_data):
        for i in range(1, 4):
            name = user_data.get(f"m{i}_name")
            if not name:
                continue
            yield {
                "name": name,
                "lv": user_data.get(f"m{i}_lv", 0),
                "hai": user_data.get(f"m{i}_hai", 0),
            }

    def create_users_list(self, start, end):
        return [
            {
                "user_name": name,
                "rank": user["rank"],
                "key": user["key"],
                "money": user["money"],
                "getm": user.get("getm", 0),
                "delday": getdelday(user["bye"]),
                "monsters": list(self.user_mlist(user)),
                "mes": user.get("mes", ""),
            }
            for name, user in islice(self.u_list.items(), start, end)
        ]


class TopPageRenderer:
    MAINTENANCE_MODE = os.path.exists("mente.mente")

    def __init__(self):
        cookie = get_cookie()
        self.in_name = cookie.get("in_name", "")
        self.in_pass = cookie.get("in_pass", "")
        self.token = secrets.token_hex(16)
        set_session({"token": self.token, "ref": "top"})

        status = get_tournament_status()
        self.t_time = status["t_time"]
        self.t_count = status["t_count"]

    def check_tournament(self):
        """トーナメント開催を確認（日時超過で実行）"""
        if self.t_count >= 0:
            return
        try:
            tournament()
        except Exception as e:
            error(f"トーナメント処理中にエラーが発生しました: {str(e)}", "top")

    def render(self, page, user_list_manager):
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
            "in_name": self.in_name,
            "in_pass": self.in_pass,
            "maintenance": self.MAINTENANCE_MODE,
            "rank_text": rank_text,
            "users": users,
            "t_count": self.t_count,
            "t_time": self.t_time,
            "u_count": user_list_manager.u_count,
            "fol": FORM.get("fol", ""),
        }
        if FORM.get("mode", "") == "view":
            print_html("top_eventlog_tmp.html", content)
        else:
            print_html("top_tmp.html", content)


if __name__ == "__main__":

    client_ip = get_client_ip()  # クライアントIPを取得

    # IPアドレスが禁止リストに含まれている場合、エラーメッセージを表示
    if is_ip_banned(client_ip):
        error("あなたのIPは禁止されています", 99)

    # フォームを辞書化
    form = cgi.FieldStorage()
    FORM = {key: form.getfirst(key) for key in form}
    # パラメーターによるセーブデータフォルダ分岐処理
    conf.apply_fol(FORM)

    try:
        page = int(FORM.get("page", "1"))
        if page not in (1, 2):
            raise ValueError
    except ValueError:
        error(f"無効なメニューです: {FORM.get('page', '1')}", "top")

    # 放置ユーザーチェック
    delete_check()

    user_list_manager = UserListManager()
    renderer = TopPageRenderer()
    renderer.render(
        page,
        user_list_manager,
    )
