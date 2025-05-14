#!D:\Python\Python312\python.exe

import cgi
import datetime
import secrets
import os
from itertools import islice

from cgi_py.tournament import tournament
from sub_def.file_ops import open_user_list, open_tournament_time
from sub_def.crypto import get_cookie, set_session
from sub_def.user_ops import getdelday, get_client_ip, delete_check, is_ip_banned
from sub_def.utils import print_html, error
import conf

Conf = conf.Conf


class StartTop:
    def __init__(self):
        self.u_list = open_user_list()
        self.u_count = len(self.u_list)

        cookie = get_cookie()
        self.in_name = cookie.get("in_name", "")
        self.in_pass = cookie.get("in_pass", "")
        self.token = secrets.token_hex(16)
        set_session({"token": self.token, "ref": "top"})

        self.maintenance = os.path.exists("mente.mente")

        self.t_time = open_tournament_time()
        self.t_count = (
            datetime.datetime.strptime(self.t_time, "%Y年%m月%d日")
            - datetime.datetime.now()
        ).days

    def check_tournament(self):
        # メダル杯開催確認
        if self.t_count < 0:
            tournament()

    def user_mlist(self, user_data):
        # ユーザーの手持ちモンスターのリストを作成
        return [
            {
                "name": user_data[f"m{i}_name"],
                "lv": user_data[f"m{i}_lv"],
                "hai": user_data[f"m{i}_hai"],
            }
            for i in range(1, 4)
            if user_data.get(f"m{i}_name")
        ]

    def create_users_list(self, start, end):
        """表示するユーザーのリストを作成する"""
        return [
            {
                "user_name": name,
                "rank": user["rank"],
                "key": user["key"],
                "money": user["money"],
                "getm": user.get("getm", 0),
                "delday": getdelday(user["bye"]),
                "monsters": self.user_mlist(user),
                "mes": user["mes"],
            }
            for name, user in islice(self.u_list.items(), start, end)
        ]

    def prepare_content(self, rank_text, users):
        content = {
            "Conf": Conf,
            "token": self.token,
            "in_name": self.in_name,
            "in_pass": self.in_pass,
            "maintenance": self.maintenance,
            "rank_text": rank_text,
            "users": users,
            "t_count": self.t_count,
            "t_time": self.t_time,
            "u_count": self.u_count,
        }
        return content

    def main_html(self, is_top):
        # メダル杯開催確認
        self.check_tournament()

        # 開始・終了インデックスを動的に決定
        max_show = Conf["maxshow"]
        start = 0 if int(is_top) else max_show
        end = max_show if int(is_top) else self.u_count

        # 必要なデータを生成
        rank_text = f"RANKING [{start + 1}位～{end}位]"
        users = self.create_users_list(start, end)

        content = self.prepare_content(rank_text, users)
        print_html("top_tmp.html", content)


if __name__ == "__main__":

    client_ip = get_client_ip()  # クライアントIPを取得

    # IPアドレスが禁止リストに含まれている場合、エラーメッセージを表示
    if is_ip_banned(client_ip):
        error("あなたのIPは禁止されています", 99)

    # フォームを辞書化
    form = cgi.FieldStorage()
    FORM = {key: form.getvalue(key) for key in form.keys()}

    # 放置ユーザーチェック
    delete_check()

    # インスタンス作成とHTML生成
    start_top_instance = StartTop()
    start_top_instance.main_html(FORM.get("menu", 1))
