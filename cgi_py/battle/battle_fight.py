# battle_fight.py 戦闘行動処理


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


def prepare_battle_commands(FORM, party):
    for i, pt in enumerate(party, 1):
        pt["bt"] = {
            "hit": FORM.get(f"hit{i}", 0),
            "target": int(FORM.get(f"target{i}", 0) or 0),
            "toku": FORM.get(f"toku{i}", 0),
            "nakama": int(FORM.get(f"nakama{i}", 0) or 0),
            "ktoku": FORM.get(f"ktoku{i}", 0),
        }


def execute_battle_actions(bm):
    # 行動順(agi)でソート
    BT = sorted(
        bm.battle["party"] + bm.battle["teki"][1:],
        key=lambda x: int(x.get("agi", 0)),
        reverse=True,
    )

    for bt in BT:
        if bt.get("no"):
            bt["休み"] = 0

    # 順番に行動を実行
    for bt in BT:
        if bt.get("hp", 0) > 0 and bt.get("休み", 0) == 0:
            if bt.get("no"):
                mikata_action(bt, bm)
            else:
                teki_action(bt, bm)

    # 次ターンに向けたクリーンアップ
    for pt in bm.battle["party"]:
        pt.pop("bt", None)
        pt.pop("休み", None)


def handle_battle_end_conditions(bm):
    is_end = False
    teki = bm.battle["teki"]
    party = bm.battle["party"]

    # 勝利条件
    if teki[0].get("down", 0) == len(teki):
        is_end = True
        battle_end("勝利した", 1, bm)

        if bm.special == "0" or bm.special == 0:
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

    # 敗北条件
    elif bm.pt_num == len([1 for pt in party if str(pt.get("hp", 0)) == "0"]):
        is_end = True
        battle_end("負けた", 0, bm)
        if bm.special in (0, "異世界"):
            haisen(bm)

    # 引き分け（規定ターン）
    elif bm.turn >= Conf.get("maxround", 20):
        is_end = True
        battle_end("引き分けた", 0.5, bm)

    return is_end


def battle_fight(FORM):
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
