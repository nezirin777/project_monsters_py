#!D:\Python\Python312\python.exe

import cgi
import datetime
import secrets
import os
from jinja2 import Environment, FileSystemLoader
import sys

import cgi_py
import sub_def
import conf

Conf = conf.Conf


class StartTop:
    def __init__(self):
        self.u_list = sub_def.open_user_list()
        self.u_count = len(self.u_list)

        cookie = sub_def.get_cookie()
        self.in_name = cookie.get("in_name", "")
        self.in_pass = cookie.get("in_pass", "")
        self.token = secrets.token_hex(16)
        sub_def.set_session({"token": self.token})
        self.maintenance = os.path.exists("mente.mente")
        self.t_time = sub_def.open_tournament_time()

        self.template_env = Environment(
            loader=FileSystemLoader("templates"), cache_size=100
        )
        self.t_count = (
            datetime.datetime.strptime(self.t_time, "%Y年%m月%d日")
            - datetime.datetime.now()
        ).days

        # メダル杯開催確認
        if int(self.t_count) < 0:
            cgi_py.tournament.tournament()

    def get_template(self, template_name):
        """テンプレートを取得"""
        return self.template_env.get_template(template_name)

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
                "delday": sub_def.getdelday(user["bye"]),
                "monsters": self.user_mlist(user),
                "mes": user["mes"],
            }
            for name, user in list(self.u_list.items())[start:end]
        ]

    def prepare_context(self, rank_text, users):
        context = {
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
        return context

    def main_html(self, is_top):
        # 開始・終了インデックスを動的に決定
        max_show = Conf["maxshow"]
        start = 0 if int(is_top) else max_show
        end = max_show if int(is_top) else self.u_count

        # 必要なデータを生成
        rank_text = f"RANKING [{start + 1}位～{end}位]"
        users = self.create_users_list(start, end)

        context = self.prepare_context(rank_text, users)
        template = self.get_template("top_tmp.html")  # テンプレート読み込みを分離
        return template.render(context)


if __name__ == "__main__":

    client_ip = sub_def.get_client_ip()  # クライアントIPを取得

    # IPアドレスが禁止リストに含まれている場合、エラーメッセージを表示
    if sub_def.is_ip_banned(client_ip):
        sub_def.error("あなたのIPは禁止されています", 99)

    # フォームを辞書化
    form = cgi.FieldStorage()
    FORM = {key: form.getvalue(key) for key in form.keys()}

    # インスタンス作成とHTML生成
    start_top_instance = StartTop()
    print("Content-Type: text/html; charset=utf-8\r\n\r\n")

    sub_def.delete_check()

    html = start_top_instance.main_html(FORM.get("menu", 1))
    print(html)
    sys.exit()
