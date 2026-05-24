# battle_fight.py 戦闘行動処理

from typing import NoReturn

from cgi_py.battle.battle_manager import BattleManager
from cgi_py.battle.battle_action import mikata_action, teki_action
from cgi_py.battle.battle_menu import battle_menu
from cgi_py.battle.battle_sub import (
    battle_end,
    battle_isekai_key_get,
    battle_isekai_limit_get,
    battle_medal_get,
    battle_roomkey_get,
    key_get,
    mon_get,
    haisen,
)

from sub_def.utils import print_html
import conf

Conf = conf.Conf


def prepare_battle_commands(FORM: dict, party: list) -> None:
    """フォームから送られた行動コマンドを解析してパーティの各モンスターに設定する"""
    for i, pt in enumerate(party, 1):

        selected_hit = FORM.get(f"hit{i}", "攻撃")
        # フォームから空文字が送られてきた場合も 0 にフォールバックする
        selected_target = int(FORM.get(f"target{i}", 0) or 0)
        selected_toku = FORM.get(f"toku{i}", "通常攻撃")
        selected_nakama = int(FORM.get(f"nakama{i}", 0) or 0)
        selected_ktoku = FORM.get(f"ktoku{i}", "0")

        pt["bt"] = {
            "hit": selected_hit,
            "target": selected_target,
            "toku": selected_toku,
            "nakama": selected_nakama,
            "ktoku": selected_ktoku,
        }

        # 次ターンのUI表示で前回のコマンドを選択済みとして再表示するために記憶する
        pt["last_hit"] = selected_hit
        pt["last_target"] = selected_target
        pt["last_toku"] = selected_toku
        pt["last_nakama"] = selected_nakama
        pt["last_ktoku"] = selected_ktoku


def execute_battle_actions(bm: BattleManager) -> None:
    """全モンスター・敵の行動を素早さ順に実行する"""
    # 味方(party)と敵(teki[1:])を合算して素早さ降順に並べた行動リスト。
    # teki[0] は集計用センチネルのため除外する
    BT = sorted(
        bm.battle["party"] + bm.battle["teki"][1:],
        key=lambda x: int(x.get("agi", 0)),
        reverse=True,
    )

    # "no" キーを持つ要素が味方モンスター（サーバーが付与するパーティ順番号）。
    # 敵は "no" を持たないため、この差異で味方/敵を識別する。
    # 行動前に「休み」フラグをリセットして、前ターンの蘇生直後の硬直が持ち越さないようにする
    for bt in BT:
        if bt.get("no"):
            bt["休み"] = 0

    # 素早さ順に行動を実行する
    for bt in BT:
        if bt.get("hp", 0) > 0 and bt.get("休み", 0) == 0:
            if bt.get("no"):
                mikata_action(bt, bm)
            else:
                teki_action(bt, bm)

    # 次ターンに向けたクリーンアップ（行動コマンドと休みフラグを除去）
    for pt in bm.battle["party"]:
        pt.pop("bt", None)
        pt.pop("休み", None)


def handle_battle_end_conditions(bm: BattleManager) -> bool:
    """
    勝利・敗北・引き分けの判定を行い、対応する報酬・ペナルティ処理を呼び出す。
    戦闘終了なら True を返す。
    """
    is_end = False
    teki = bm.battle["teki"]
    party = bm.battle["party"]

    # 勝利条件:
    # teki[0].down は初期値 1 から始まり、敵を倒すごとに +1 される。
    # len(teki) はセンチネル(teki[0])を含む全要素数なので、
    # down == len(teki) のとき「全員撃破」を意味する
    if teki[0].get("down", 0) == len(teki):
        is_end = True
        battle_end("勝利した", 1, bm)

        if bm.special == "normal":
            key_get(bm)
            mon_get(bm)
        elif bm.special == "スライム":
            battle_roomkey_get(bm)
        elif bm.special == "わたぼう":
            battle_medal_get(bm)
        elif bm.special == "vipsg":
            battle_isekai_limit_get(bm)
        elif bm.special == "異世界":
            battle_isekai_key_get(bm)
            mon_get(bm)

    # 敗北条件: 出撃数(pt_num)分のモンスターが全員 HP0
    # hp は int と文字列 "0" が混在し得るため str 変換で統一して比較する
    elif bm.pt_num == sum(str(pt.get("hp", 0)) == "0" for pt in party):
        is_end = True
        battle_end("負けた", 0, bm)

        # 通常戦闘と異世界戦闘では敗北時に鍵を失う
        if bm.special in ("normal", "異世界"):
            haisen(bm)

        # 全滅時は先頭のみ HP1 で復活（次戦に備えるため）
        if bm.battle["party"]:
            bm.battle["party"][0]["hp"] = 1

    # 引き分け条件: 規定ターン数に達した
    elif bm.turn >= Conf.get("maxround", 20):
        is_end = True
        battle_end("引き分けた", 0.5, bm)

    return is_end


def battle_fight(FORM: dict) -> NoReturn:
    """戦闘行動処理の CGI エントリポイント"""
    # マネージャー（すべての状態を持つ）を起動
    bm = BattleManager(FORM)
    bm.next_turn_setup()

    # コマンドのパースとアクション実行
    prepare_battle_commands(FORM, bm.battle["party"])
    execute_battle_actions(bm)

    # 終了判定
    is_end = handle_battle_end_conditions(bm)

    # 全データの保存
    bm.save_all()

    # 表示データの構築とレンダリング
    menu_data = None if is_end else battle_menu(FORM, bm.special)

    print_html(
        "battle_layout_tmp.html",
        {
            "Conf": Conf,
            "token": bm.session.get("token", ""),
            "action_logs": bm.action_logs,
            "system_logs": bm.system_logs,
            "menu_data": menu_data,
            "is_end": is_end,
        },
    )
    # print_html は NoReturn のためここには到達しない（型チェッカー向け）
    raise RuntimeError("unreachable")
