# tournament.py - トーナメント処理

import random
import os
from concurrent.futures import ThreadPoolExecutor
from jinja2 import Environment, FileSystemLoader

from sub_def.file_ops import (
    open_user_list,
    open_tournament_time,
    timesyori,
    open_user_all,
    save_user_all,
)
from sub_def.user_ops import backup
from sub_def.utils import error

import conf

Conf = conf.Conf

# Jinja2テンプレート環境を設定
env = Environment(loader=FileSystemLoader("templates"))


class Tournament:
    def __init__(self):
        # メンバ
        u_list = open_user_list()
        self.U_count = min(len(u_list), 64)

        # 万が一keyが存在しない場合に備えて .get を使用
        self.fighters = [
            {"name": name, "key": int(u.get("key", 1))}
            for name, u in list(u_list.items())[: self.U_count]
        ]
        self.new_F = []
        self.present = []

        self.b_data = {
            "第一回戦": {"menber": 32, "hosei": 16, "medal": 1},
            "第二回戦": {"menber": 16, "hosei": 8, "medal": 2},
            "第三回戦": {"menber": 8, "hosei": 4, "medal": 3},
            "第四回戦": {"menber": 4, "hosei": 3, "medal": 5},
            "準決勝": {"menber": 2, "hosei": 2, "medal": 7},
            "決勝戦": {"menber": 1, "hosei": 1, "medal": 10},
        }

        # テンプレートへ渡す用の構造化データ
        self.log_data = {
            "status": "success",
            "title": "未開催",
            "rounds": [],
            "champion": None,
            "champ_medal": 0,
        }

    def medal_get(self):
        """並列処理でメダルを付与（user_all対応・安全版）"""

        def update_user(target, medal):
            all_data = open_user_all(target)
            user = all_data.get("user", {})
            user["medal"] = int(user.get("medal", 0)) + medal
            all_data["user"] = user
            save_user_all(all_data, target)

        with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as executor:
            futures = [
                executor.submit(update_user, p["target"], p["medal"])
                for p in self.present
            ]
            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    import sys

                    print(f"[ERROR] メダル付与エラー: {e}", file=sys.stderr)

        self.present.clear()

    def determine_winner(self, fighter1, fighter2, boost):
        """勝者と敗者を決定"""
        stats = [
            {"hp": boost["hosei"], "atk": boost["hosei"] + random.randint(1, 10)},
            {"hp": 1, "atk": 1 + random.randint(1, 10)},
        ]
        stats[1]["hp"] -= max(0, stats[0]["atk"] - stats[1]["atk"])
        stats[0]["hp"] -= max(0, stats[1]["atk"] - stats[0]["atk"])

        return (
            (fighter1, fighter2)
            if stats[0]["hp"] >= stats[1]["hp"]
            else (fighter2, fighter1)
        )

    def process_round(self, round_name, boost):
        """1回戦分の処理（文字列結合ではなく辞書を作成する）"""
        next_round = []
        round_info = {"name": round_name, "matches": []}

        i = 1
        while len(self.fighters) > 1:
            fighter1, fighter2 = random.sample(self.fighters, 2)
            winner, loser = self.determine_winner(fighter1, fighter2, boost)

            # 試合情報を辞書として保存
            match_info = {
                "num": i if round_name != "決勝戦" else None,
                "fighter1": fighter1["name"],
                "fighter2": fighter2["name"],
                "winner": winner["name"],
                "loser": loser["name"],
                "medal": boost["medal"],
            }
            round_info["matches"].append(match_info)

            if round_name != "決勝戦":
                i += 1

            # 次ラウンドの選手と報酬記録
            next_round.append(winner)
            self.present.append({"medal": boost["medal"], "target": loser["name"]})

            self.fighters.remove(fighter1)
            self.fighters.remove(fighter2)

        # 参加人数が奇数で1人余った場合、その人は「不戦勝」として次へ
        if self.fighters:
            next_round.extend(self.fighters)

        self.fighters = next_round

        # ログデータにこのラウンドの結果を追加
        self.log_data["rounds"].append(round_info)

    def t_battle(self):
        """トーナメントの実行とHTMLファイル生成"""

        self.log_data["title"] = f"{open_tournament_time()} のメダル獲得杯の結果！"

        if self.U_count < 2:
            self.log_data["status"] = "cancel"
        else:
            for round_name, boost in self.b_data.items():
                if len(self.fighters) <= 1:
                    break
                self.process_round(round_name, boost)

            # 優勝者への報酬
            if self.fighters:
                champion = self.fighters[0]
                val = random.randint(13, 15)
                self.present.append({"medal": val, "target": champion["name"]})
                self.log_data["champion"] = champion["name"]
                self.log_data["champ_medal"] = val

        # ================================
        # Jinja2で静的HTMLを生成して保存
        # ================================
        try:
            template = env.get_template("tournament_result_tmp.html")
            context = {
                "Conf": Conf,
                "log_data": self.log_data,
            }
            html_output = template.render(context)

            # htmlフォルダに静的ファイルとして保存
            os.makedirs("html", exist_ok=True)
            with open("html/tournament_result.html", "w", encoding="utf-8") as f:
                f.write(html_output)

        except Exception as e:
            error(
                f"トーナメント結果HTMLの生成中にエラーが発生しました: {e}", jump="top"
            )

        self.medal_get()
        backup()


def tournament():
    Tournament().t_battle()

    # 次の開催日時を記録
    timesyori()
