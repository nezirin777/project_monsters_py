# battle_manager.py 戦闘処理管理

import time
import conf
from sub_def.file_ops import (
    open_user_all,
    save_user_all,
    open_battle,
    save_battle,
    open_tokugi_dat,
    open_seikaku_dat,
)
from sub_def.crypto import set_session
from sub_def.utils import slim_number_with_cookie, error

Conf = conf.Conf


class BattleManager:
    def __init__(self, FORM):
        self.FORM = FORM
        self.session = FORM.get("s", {})
        self.user_name = self.session.get("in_name")

        if not self.user_name:
            error("ユーザー名が取得できませんでした。", "top")

        # ユーザーデータの読み込み
        self.all_data = open_user_all(self.user_name)
        self.user = self.all_data.get("user", {})
        self.party = self.all_data.get("party", [])
        self.vips = self.all_data.get("vips", {})
        self.zukan = self.all_data.get("zukan", {})
        self.room_key = self.all_data.get("room_key", {})

        # バトルデータ・マスタデータの読み込み
        self.battle = open_battle(self.user_name)
        if not self.battle or "teki" not in self.battle or not self.battle["teki"]:
            error(
                "バトルデータが消失しました。<br>マイページからやり直してください。",
                "my_page",
            )

        self.tokugi_dat = open_tokugi_dat()
        self.seikaku_dat = open_seikaku_dat()

        # 状態変数の取得
        self.special = self.session.get("special", 0)
        self.in_floor = (
            int(self.session.get("last_floor_isekai", 0))
            if self.special == "異世界"
            else int(self.session.get("last_floor", 0))
        )
        self.turn = int(self.session.get("turn", 1))

        self.pt_num = (
            1
            if self.special in ("わたぼう", "スライム")
            else min(len(self.battle.get("party", [])), 3)
        )

        # ログ保管用リスト
        self.action_logs = []
        self.system_logs = []

    def next_turn_setup(self):
        """ターン進行と時間制限の更新"""
        next_t = time.time() + Conf["nextplay"]
        self.session["next_t"] = next_t
        self.session["turn"] = self.turn + 1
        set_session(self.session)
        self.user["next_t"] = next_t

    def save_all(self):
        """全てのデータを一括で永続化する"""
        # 戦闘中のステータス変更を大元のpartyに反映
        for i, pt in enumerate(self.battle.get("party", [])):
            if i < len(self.party):
                self.party[i] = pt

        if self.party and self.party[0].get("hp", 0) == 0:
            self.party[0]["hp"] = 1

        self.all_data["user"] = self.user
        self.all_data["party"] = self.party

        save_user_all(self.all_data, self.user_name)
        save_battle(self.battle, self.user_name)

    # ===============================
    # ログ記録用メソッド群
    # ===============================
    def log_action(self, actor, target, event_data):
        """行動ログの追加"""
        self.action_logs.append(
            {
                "turn": self.turn,
                "actor": slim_number_with_cookie(actor),
                "target": slim_number_with_cookie(target) if target else None,
                "text": event_data,
            }
        )

    def log_custom(self, log_dict):
        """特殊なログ（レベルアップ、アイテムドロップ等）の追加"""
        if log_dict:
            self.system_logs.append(log_dict)
