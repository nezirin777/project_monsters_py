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
    log,
)
from sub_def.user_ops import backup
from sub_def.utils import error

import conf

Conf = conf.Conf

# Jinja2テンプレート環境を設定
env = Environment(loader=FileSystemLoader("templates"))


def _update_user_medal(target: str, medal: int) -> None:
    """1ユーザーへメダルを加算して保存する（ThreadPoolExecutor から呼ばれる）"""
    all_data = open_user_all(target)
    user = all_data.get("user", {})
    user["medal"] = int(user.get("medal", 0)) + medal
    all_data["user"] = user
    save_user_all(all_data, target)


class Tournament:
    def __init__(self) -> None:
        u_list = open_user_list()
        self.U_count = min(len(u_list), 64)

        # 万が一 key が存在しない場合に備えて .get を使用
        self.fighters: list[dict] = [
            {"name": name, "key": int(u.get("key", 1))}
            for name, u in list(u_list.items())[: self.U_count]
        ]
        self.new_F: list = []

        # 各ラウンドの設定。hosei は勝者側の強さ補正、medal は敗者への付与枚数
        # ※ member キーは現在未使用だが将来の拡張用として残している
        self.b_data: dict[str, dict] = {
            "第一回戦": {"member": 32, "hosei": 16, "medal": 1},
            "第二回戦": {"member": 16, "hosei": 8, "medal": 2},
            "第三回戦": {"member": 8, "hosei": 4, "medal": 3},
            "第四回戦": {"member": 4, "hosei": 3, "medal": 5},
            "準決勝": {"member": 2, "hosei": 2, "medal": 7},
            "決勝戦": {"member": 1, "hosei": 1, "medal": 10},
        }

        # メダル付与キュー。(target, medal) の形で蓄積し medal_get() で一括処理する
        self.present: list[dict] = []

        # テンプレートへ渡す用の構造化データ
        self.log_data: dict = {
            "status": "success",
            "title": "未開催",
            "rounds": [],
            "champion": None,
            "champ_medal": 0,
        }

    def medal_get(self) -> None:
        """並列処理でメダルを付与する"""
        with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as executor:
            futures = [
                executor.submit(_update_user_medal, p["target"], p["medal"])
                for p in self.present
            ]
            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    # 1件の失敗で全体を止めないよう警告ログだけ出して続行する
                    log(f"[ERROR] メダル付与エラー: {e}")

        self.present.clear()

    def determine_winner(
        self, fighter1: dict, fighter2: dict, boost: dict
    ) -> tuple[dict, dict]:
        """
        勝者と敗者を決定して (winner, loser) のタプルで返す。

        boost["hosei"] を勝者側の HP ボーナスとして加算し、
        両者の atk にランダム係数を乗せて最終的な HP で勝敗を判定する。
        """
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

    def process_round(self, round_name: str, boost: dict) -> None:
        """1ラウンド分の試合を処理してログデータに追記する"""
        next_round: list[dict] = []
        round_info: dict = {"name": round_name, "matches": []}

        # 決勝戦は試合番号を表示しないため match_num を使い分ける
        is_final = round_name == "決勝戦"
        match_num = 0

        while len(self.fighters) > 1:
            fighter1, fighter2 = random.sample(self.fighters, 2)
            winner, loser = self.determine_winner(fighter1, fighter2, boost)

            if not is_final:
                match_num += 1

            match_info = {
                "num": None if is_final else match_num,
                "fighter1": fighter1["name"],
                "fighter2": fighter2["name"],
                "winner": winner["name"],
                "loser": loser["name"],
                "medal": boost["medal"],
            }
            round_info["matches"].append(match_info)

            next_round.append(winner)
            self.present.append({"medal": boost["medal"], "target": loser["name"]})

            self.fighters.remove(fighter1)
            self.fighters.remove(fighter2)

        # 参加人数が奇数で1人余った場合、その人は不戦勝として次ラウンドへ進む
        if self.fighters:
            next_round.extend(self.fighters)

        self.fighters = next_round
        self.log_data["rounds"].append(round_info)

    def t_battle(self) -> None:
        """トーナメントを実行し、結果を静的 HTML ファイルとして書き出す"""
        self.log_data["title"] = f"{open_tournament_time()} のメダル獲得杯の結果！"

        if self.U_count < 2:
            # 規定人数未満の場合は中止扱い
            self.log_data["status"] = "cancel"
        else:
            for round_name, boost in self.b_data.items():
                if len(self.fighters) <= 1:
                    break
                self.process_round(round_name, boost)

            # 優勝者へのメダル付与
            if self.fighters:
                champion = self.fighters[0]
                val = random.randint(13, 15)
                self.present.append({"medal": val, "target": champion["name"]})
                self.log_data["champion"] = champion["name"]
                self.log_data["champ_medal"] = val

        # ================================
        # Jinja2 で静的 HTML を生成して保存
        # ================================
        try:
            template = env.get_template("tournament_result_tmp.html")
            context = {
                "Conf": Conf,
                "log_data": self.log_data,
            }
            html_output = template.render(context)

            os.makedirs("html", exist_ok=True)
            with open("html/tournament_result.html", "w", encoding="utf-8") as f:
                f.write(html_output)

        except Exception as e:
            error(
                f"トーナメント結果HTMLの生成中にエラーが発生しました: {e}", jump="top"
            )

        self.medal_get()
        backup()


def tournament() -> None:
    """トーナメントを実行し、次回開催日時を記録する"""
    Tournament().t_battle()
    timesyori()
