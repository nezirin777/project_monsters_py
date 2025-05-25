import random
import os
from concurrent.futures import ThreadPoolExecutor

import sub_def
import conf

Conf = conf.Conf


class Tournament:
    def __init__(self):

        # メンバ
        u_list = sub_def.open_user_list()
        self.U_count = min(len(u_list), 64)
        self.fighters = [
            {"name": name, "key": u["key"]}
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

    def medal_get(self):
        """並列処理でメダルを付与"""

        def update_user(target, medal):
            user = sub_def.open_user(target)
            user["medal"] += medal
            sub_def.save_user(user, target)

        with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
            futures = [
                executor.submit(update_user, p["target"], p["medal"])
                for p in self.present
            ]
            for future in futures:
                future.result()  # 例外をキャッチするために結果を待機

        self.present.clear()  # リストをクリア

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
        """1回戦分の処理"""
        round_results = []
        next_round = []

        i = 1
        while len(self.fighters) > 1:
            fighter1, fighter2 = random.sample(self.fighters, 2)
            winner, loser = self.determine_winner(fighter1, fighter2, boost)

            match_result = ""
            if round_name != "決勝戦":
                match_result = f"""<div class="medal_battle_sub">第{i}試合</div>\n"""
                i += 1

            # 結果テキスト
            match_result += f"{fighter1['name']} vs {fighter2['name']} は {winner['name']} さんが勝利しました"
            reward_text = (
                f"{loser['name']} さんにメダル {boost['medal']} 枚が与えられました"
            )

            # 次ラウンドの選手と報酬記録
            next_round.append(winner)
            self.present.append({"medal": boost["medal"], "target": loser["name"]})

            # 結果収集
            round_results.append(
                f"<div class='medal_battle_result'>{match_result}</div>{reward_text}"
            )
            self.fighters.remove(fighter1)
            self.fighters.remove(fighter2)

        self.fighters = next_round
        return "".join(round_results)

    def t_battle(self):
        """トーナメントの実行"""
        tournament_log = f"<div class='medal_battle_title'>{sub_def.open_tournament_time()} のメダル獲得杯の結果！</div>"

        if self.U_count < 2:
            tournament_log += "<div>規定人数未満につき中止になりました。</div>"
        else:
            for round_name, boost in self.b_data.items():
                if len(self.fighters) <= 1:
                    break

                round_log = self.process_round(round_name, boost)
                tournament_log += f"<div><div class='medal_battle_data'>{round_name}</div>{round_log}</div>"

            # 優勝者への報酬
            if self.fighters:
                champion = self.fighters[0]
                val = random.randint(13, 15)
                self.present.append({"medal": val, "target": champion["name"]})
                tournament_log += f"<div class='red'>優勝の {champion['name']} さんにメダル {val} 枚が与えられました</div>"

        # 結果保存
        try:
            with open(
                os.path.join(Conf["savedir"], "tournament.log"), "w", encoding="utf-8"
            ) as f:
                f.write(tournament_log)
        except IOError as e:
            sub_def.error(f"トーナメント結果の保存中にエラーが発生しました: {e}")

        self.medal_get()
        sub_def.backup()


def tournament():
    Tournament().t_battle()

    # 次の開催日時を記録
    sub_def.timesyori()
