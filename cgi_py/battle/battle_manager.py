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
    def __init__(self, FORM: dict) -> None:
        self.FORM = FORM
        self.session: dict = FORM.get("s", {})
        self.user_name: str = self.session.get("in_name")

        if not self.user_name:
            error("ユーザー名が取得できませんでした。", "top")

        # ユーザーデータの読み込み
        self.all_data: dict = open_user_all(self.user_name)
        self.user: dict = self.all_data.get("user", {})
        self.party: list = self.all_data.get("party", [])
        self.vips: dict = self.all_data.get("vips", {})
        self.room_key: dict = self.all_data.get("room_key", {})

        # バトルデータ・マスタデータの読み込み
        self.battle: dict = open_battle(self.user_name)
        if not self.battle or "teki" not in self.battle or not self.battle["teki"]:
            error(
                "バトルデータが消失しました。<br>マイページからやり直してください。",
                "my_page",
            )

        self.tokugi_dat: dict = open_tokugi_dat()
        self.seikaku_dat: dict = open_seikaku_dat()

        # 状態変数の取得
        # デフォルト "normal" はセッションに値がない古いデータとの互換のため
        self.special: str = self.session.get("special", "normal")

        # 異世界戦闘と通常戦闘では参照するセッションキーが異なる
        self.in_floor: int = (
            int(self.session.get("last_floor_isekai", 0))
            if self.special == "異世界"
            else int(self.session.get("last_floor", 0))
        )
        self.turn: int = int(self.session.get("turn", 1))

        # わたぼう・スライム戦は先頭1体のみ出撃。通常・異世界は最大3体
        self.pt_num: int = (
            1
            if self.special in ("わたぼう", "スライム")
            else min(len(self.battle.get("party", [])), 3)
        )

        # ログ保管用リスト（action: ターン毎の行動、system: LVアップ等のイベント）
        self.action_logs: list[dict] = []
        self.system_logs: list[dict] = []

    def next_turn_setup(self) -> None:
        """ターン進行と時間制限の更新"""
        next_t = time.time() + Conf["nextplay"]
        self.session["next_t"] = next_t
        # self.turn はこのターンの番号として読み取り専用で使う。
        # 次ターン番号はセッション側に書き込み、リロード時に再取得する設計のため
        # self.turn 自体は更新しない
        self.session["turn"] = self.turn + 1
        set_session(self.session)
        self.user["next_t"] = next_t

    def save_all(self) -> None:
        """全てのデータを一括で永続化する"""
        # 戦闘中のステータス変更を大元のpartyに反映
        for i, pt in enumerate(self.battle.get("party", [])):
            if i < len(self.party):
                self.party[i] = pt

        self.all_data["user"] = self.user
        self.all_data["party"] = self.party

        save_user_all(self.all_data, self.user_name)
        save_battle(self.battle, self.user_name)

    # ===============================
    # ログ記録用メソッド群
    # ===============================
    def log_action(self, actor: dict, target: dict | None, event_data: dict) -> None:
        """行動ログの追加"""
        self.action_logs.append(
            {
                "turn": self.turn,
                "actor": slim_number_with_cookie(actor),
                "target": slim_number_with_cookie(target) if target else None,
                "text": event_data,
            }
        )

    def log_custom(self, log_dict: dict | None) -> None:
        """特殊なログ（レベルアップ、アイテムドロップ等）の追加"""
        if log_dict:
            self.system_logs.append(log_dict)
