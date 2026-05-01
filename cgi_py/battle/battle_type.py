# battle_type.py 戦闘種類分け

import time
import random
from cgi_py.battle.battle_menu import battle_menu
from sub_def.file_ops import (
    open_user_all,
    save_user_all,
    save_battle,
    open_monster_dat,
    open_monster_boss_dat,
)
from sub_def.monster_ops import battle_mob_select, battle_boss_select
from sub_def.crypto import set_session
from sub_def.utils import error, print_html, slim_number_with_cookie
import conf

Conf = conf.Conf


class BattleStarter:
    """戦闘開始前のバリデーションと敵選出、セットアップを全て管理するクラス"""

    def __init__(self, FORM):
        self.FORM = FORM
        self.session = FORM.get("s", {})
        self.user_name = self.session.get("in_name")

        if not self.user_name:
            error("ユーザー名が取得できませんでした。", jump="top")

        # データを一括で読み込み（クラス内の共通変数として保持）
        self.all_data = open_user_all(self.user_name)
        self.user = self.all_data.get("user", {})
        self.party = self.all_data.get("party", [])
        self.vips = self.all_data.get("vips", {})
        self.room_key = self.all_data.get("room_key", {})

    def validate(self, in_floor=None, in_isekai=None):
        """ユーザーとパーティの状態をチェック"""
        if in_floor is not None:
            if not (0 < in_floor <= self.user.get("key", 1)):
                error("階層指定がおかしいです", jump="my_page")

        if in_isekai is not None:
            if not (0 <= in_isekai <= self.user.get("isekai_key", 0)):
                error("異世界は1Fづつしか進めません。", jump="my_page")
            if in_isekai > self.user.get("isekai_limit", 0):
                error("探索限界に達しています", jump="my_page")

        if len(self.party) < 1:
            error("パーティがいません。<br>最低1体は必要です。", jump="my_page")

        if self.party[0].get("hp", 0) <= 0:
            error(
                "先頭のモンスターのHPが0です。<br>回復するか他のモンスターにしてください。",
                jump="my_page",
            )

    def determine_special_enemy(self, in_floor):
        """特殊敵（わたぼう等）を判定する"""
        vip_boost = self.vips.get("boost")
        event_boost = Conf.get("event_boost")

        randam = 0
        if event_boost and vip_boost:
            randam = 15
        elif event_boost or vip_boost:
            randam = 20
        else:
            randam = 25

        special_enemies = ["わたぼう"] if random.randint(1, randam) == 1 else []

        if "わたぼう" in special_enemies:
            if any(r_key.get("get", 0) == 0 for r_key in self.room_key.values()):
                special_enemies.append("スライム")

            if in_floor >= 1001 + 500 * (self.user.get("isekai_limit", 0) / 10):
                # ↑500階おきに次のエリアに進めるようになる
                if self.user.get("isekai_limit", 0) < self.user.get("isekai_key", 0):
                    if self.user.get("isekai_limit", 0) != Conf.get("isekai_max_limit"):
                        special_enemies.append("vipsg")

        return special_enemies or [0]

    # ==========================================
    # ここから旧 battle_encount.py の統合ロジック
    # ==========================================
    def _calculate_floor_and_hosei(self, floor, special_monster):
        # 階層と補正値を計算
        kaisou = floor
        while kaisou > 500:
            kaisou -= 500

        base_hosei = floor * (floor / 500 if floor > 500 else 1)
        user_key = (
            self.user.get("key", 0) if special_monster in ("vipsg", "異世界") else 0
        )

        # 特殊モンスターによる補正計算を定義
        if special_monster in ("わたぼう", "スライム"):
            hosei = (floor + 30) * ((floor / 500) * 1.3 if floor > 500 else 1)
        elif special_monster == "vipsg":
            hosei = (floor + 100) * (user_key / 2000)
        elif special_monster == "異世界":
            hosei = (floor + user_key) * ((floor + user_key) / 500)
        else:
            hosei = base_hosei

        return kaisou, hosei, user_key

    # モンスターリストのフィルタリング
    def _get_monster_list(self, floor, room_type, special_monster):
        monsters = (
            open_monster_boss_dat()
            if special_monster == "vipsg"
            else open_monster_dat()
        )

        if special_monster == "vipsg":
            return [
                name
                for name, mon in monsters.items()
                if mon.get("type") == "VIPSガールズ"
            ]

        aite = [
            name
            for name, mon in monsters.items()
            if mon.get("階層A", 0) <= floor <= mon.get("階層B", 0)
            and (
                room_type == "通常"
                and mon.get("room") not in ("異世界", "？？？系")
                or room_type == mon.get("room")
            )
        ]

        # きゅうべぇ出現判定
        if special_monster == "異世界" and 21 <= floor <= 30:
            for member in self.party[:3]:
                member_mon = monsters.get(member.get("name"))
                if member_mon and member_mon.get("room") == "異世界":
                    aite.append("キュゥべえ")

        if not aite:
            error("対戦相手モンスターを選択できませんでした。", jump="my_page")
        return aite

    def _prepare_teki_list(
        self, monster_names, hosei, floor, special_monster, user_key
    ):
        teki = [{"name": "", "exp": 0, "money": 0, "down": 1}]

        if special_monster in ("わたぼう", "スライム"):
            teki.append(battle_mob_select(special_monster, hosei, floor))
            return teki

        if special_monster == "vipsg":
            selected_monsters = random.sample(
                monster_names, k=min(3, len(monster_names))
            )
            teki += [
                battle_boss_select(name, hosei, user_key) for name in selected_monsters
            ]
            return teki

        if special_monster == "異世界":
            selected_monsters = random.sample(
                monster_names, k=min(3, len(monster_names))
            )
            teki.extend(
                battle_mob_select(name, hosei, floor + user_key)
                for name in selected_monsters
            )
            return teki

        teki_kazu = random.choices([1, 2, 3], k=1, weights=[3, 2, 1])[0]
        selected_monsters = random.choices(monster_names, k=teki_kazu)
        teki.extend(
            [battle_mob_select(name, hosei, floor) for name in selected_monsters]
        )

        # 重複名の調整（A, B, C...）
        name_counts = {}
        for entry in teki[1:]:
            name = entry.get("name")
            if not name:
                continue
            if name in name_counts:
                name_counts[name] += 1
                if "name2" in entry:
                    entry["name2"] += f"_{chr(64 + name_counts[name])}"
            else:
                name_counts[name] = 1

        return teki

    # ==========================================
    # メイン処理
    # ==========================================
    def process_battle(self, special, floor_key, floor_value, room_value=None):
        """バトルの初期化と保存を処理し、画面を出力する"""

        # 1. セッションおよびユーザーデータの更新
        next_t = time.time() + Conf["nextplay"]
        self.session[floor_key] = floor_value
        self.user[floor_key] = floor_value

        if room_value is not None:
            self.session["last_room"] = room_value
            self.user["last_room"] = room_value

        self.session["special"] = special
        self.session["next_t"] = next_t
        self.session["turn"] = 1
        self.user["next_t"] = next_t

        # 2. エンカウント生成（旧battle_encount）
        in_room = room_value or "通常"
        kaisou, hosei, user_key = self._calculate_floor_and_hosei(floor_value, special)
        monster_names = self._get_monster_list(kaisou, in_room, special)
        teki = self._prepare_teki_list(
            monster_names, hosei, floor_value, special, user_key
        )

        pt_num = 1 if special in ("わたぼう", "スライム") else min(len(self.party), 3)

        # 3. データの永続化
        save_battle({"party": self.party[:pt_num], "teki": teki}, self.user_name)

        self.all_data["user"] = self.user
        save_user_all(self.all_data, self.user_name)

        set_session(self.session)
        self.FORM["s"] = self.session

        # 4. 画面出力データの構築
        encount_data = {"target": special, "tekis": slim_number_with_cookie(teki)[1:]}
        menu_data = battle_menu(self.FORM, special)

        print_html(
            "battle_layout_tmp.html",
            {
                "Conf": Conf,
                "token": self.session.get("token", ""),
                "encount_data": encount_data,
                "menu_data": menu_data,
            },
        )


# ==========================================
# CGIからのエントリーポイント
# ==========================================


def battle_type(FORM):
    """通常のバトルエントリーポイント"""
    starter = BattleStarter(FORM)
    in_floor = int(FORM.get("in_floor", 1))
    in_room = FORM.get("in_room", "")

    starter.validate(in_floor=in_floor)
    special_enemies = starter.determine_special_enemy(in_floor)
    selected_enemy = random.choice(special_enemies)

    starter.process_battle(selected_enemy, "last_floor", in_floor, room_value=in_room)


def battle_type2(FORM):
    """異世界のバトルエントリーポイント"""
    starter = BattleStarter(FORM)
    in_isekai = int(FORM.get("in_isekai", 0))

    starter.validate(in_isekai=in_isekai)
    starter.process_battle("異世界", "last_floor_isekai", in_isekai)
