# battle_fight.py - 戦闘行動前処理

import time
import conf
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
from sub_def.file_ops import (
    open_battle,
    save_battle,
    open_user_all,
    save_user_all,
    open_tokugi_dat,
    open_seikaku_dat,
)
from sub_def.crypto import set_session
from sub_def.utils import error, print_html

Conf = conf.Conf


def initialize_battle(session):
    """セッションからバトルの基本情報を取得"""
    special = session.get("special", 0)

    # 異世界の場合は参照する階層キーを変える
    if special == "異世界":
        in_floor = int(session.get("last_floor_isekai", 0))
    else:
        in_floor = int(session.get("last_floor", 0))

    if in_floor <= 0:
        error("階層選択がおかしいです？", "top")

    turn = int(session.get("turn", 1))

    return in_floor, special, turn


def next_turn_setup(session, turn, user_name):
    """次のターンの準備（時間制限とターン数の更新）"""
    next_t = time.time() + Conf["nextplay"]

    # セッション更新
    session["next_t"] = next_t
    session["turn"] = turn + 1
    set_session(session)

    # ユーザーデータ側にも時間制限を保存
    all_data = open_user_all(user_name)
    user = all_data.get("user", {})
    user["next_t"] = next_t
    all_data["user"] = user
    save_user_all(all_data, user_name)


def setup_battle_data(special, user_name):
    """バトルデータを読み込み、参加人数を決定"""
    battle = open_battle(user_name)
    if not battle or "party" not in battle:
        error("バトルデータが見つかりません。", "top")

    pt_num = min(len(battle["party"]), 3)
    if special in ("わたぼう", "スライム"):
        pt_num = 1

    return battle, pt_num


def prepare_battle_commands(FORM, party):
    """フォームから送信されたコマンドをパーティメンバーに割り当てる"""
    bt_list = []

    for i in range(1, 4):
        bt_list.append(
            {
                "hit": FORM.get(f"hit{i}", 0),
                "target": int(FORM.get(f"target{i}", 0) or 0),
                "toku": FORM.get(f"toku{i}", 0),
                "nakama": int(FORM.get(f"nakama{i}", 0) or 0),
                "ktoku": FORM.get(f"ktoku{i}", 0),
            }
        )

    for pt, b in zip(party, bt_list):
        pt["bt"] = b

    return bt_list


def execute_battle_actions(BT, battle, special, in_floor, turn):
    """素早さ順にソートされたキャラクターの行動を実行し、ログをまとめる"""
    Tokugi_dat = open_tokugi_dat()
    Seikaku_dat = open_seikaku_dat()

    action_logs = []

    # 味方の休みフラグを初期化
    for bt in BT:
        if bt.get("no"):
            bt["休み"] = 0

    for bt in BT:
        if bt.get("hp", 0) > 0 and bt.get("休み", 0) == 0:
            if bt.get("no"):
                battle, log_dict = mikata_action(
                    bt, battle, Tokugi_dat, Seikaku_dat, turn, Conf
                )
            else:
                battle, log_dict = teki_action(
                    bt, battle, special, in_floor, turn, Conf
                )

            if log_dict:
                action_logs.append(log_dict)  # ★辞書をリストに追加

    return battle, action_logs


def handle_battle_end_conditions(
    FORM, battle, pt_num, special, in_floor, turn, user_name
):
    """戦闘の終了判定（勝利・敗北・引き分け）と報酬処理のログ生成"""
    is_end = False
    session = FORM.get("s", {})
    token = session.get("token")

    # データを一括取得
    all_data = open_user_all(user_name)
    system_logs = []

    if battle["teki"][0].get("down", 0) == len(battle["teki"]):
        is_end = True
        all_data, logs = battle_end("勝利した", 1, special, all_data, battle)
        system_logs.extend(logs)

        if special == 0:
            log1 = key_get(in_floor, all_data["user"], all_data["vips"])
            log2 = mon_get(in_floor, special, battle)
            if log1:
                system_logs.append(log1)
            if log2:
                system_logs.append(log2)
        elif special == "スライム":
            log = battle_roomkey_get(all_data.get("room_key", {}))
            if log:
                system_logs.append(log)

        elif special == "わたぼう":
            log = battle_medal_get(in_floor, all_data["user"], all_data["vips"])
            if log:
                system_logs.append(log)
        elif special == "vipsg":
            log = battle_isekai_limit_get(all_data["user"])
            if log:
                system_logs.append(log)
        elif special == "異世界":
            log1 = battle_isekai_key_get(
                int(session.get("last_floor_isekai", 0)), all_data["user"]
            )
            log2 = mon_get(in_floor, special, token, battle, all_data.get("zukan", {}))
            if log1:
                system_logs.append(log1)
            if log2:
                system_logs.append(log2)

    # 敗北条件：味方が全滅
    elif pt_num == len([1 for pt in battle["party"] if str(pt.get("hp", 0)) == "0"]):
        is_end = True

        all_data, logs = battle_end("負けた", 0, special, all_data, battle)
        system_logs.extend(logs)

        if special in (0, "異世界"):
            log = haisen(all_data["user"])
            if log:
                system_logs.append(log)

    # 引き分け条件：規定ターンオーバー
    elif turn >= Conf.get("maxround", 20):
        is_end = True

        all_data, logs = battle_end("引き分けた", 0.5, special, all_data, battle)
        system_logs.extend(logs)

    # 最終的なデータの保存はここ1回で行う
    save_user_all(all_data, user_name)

    return is_end, system_logs


def battle_fight(FORM):
    """バトルのターン処理メイン関数"""
    session = FORM.get("s", {})
    user_name = session.get("in_name")

    if not user_name:
        error("ユーザー名が取得できませんでした。", "top")

    # 初期化とターン処理
    in_floor, special, turn = initialize_battle(session)
    next_turn_setup(session, turn, user_name)

    # コマンド準備と行動順決定
    battle, pt_num = setup_battle_data(special, user_name)
    prepare_battle_commands(FORM, battle["party"])

    BT = sorted(
        battle["party"] + battle["teki"][1:],
        key=lambda x: int(x.get("agi", 0)),
        reverse=True,
    )

    # アクション実行とログ受け取り
    battle, action_logs = execute_battle_actions(BT, battle, special, in_floor, turn)

    # 次のターンや保存のために不要な一時データを削除
    for pt in battle["party"]:
        pt.pop("bt", None)
        pt.pop("休み", None)

    save_battle(battle, user_name)

    # 終了判定と報酬ログの受け取り
    is_end, system_logs = handle_battle_end_conditions(
        FORM, battle, pt_num, special, in_floor, turn, user_name
    )

    menu_data = None
    if not is_end:
        menu_data = battle_menu(FORM, special)

    # ★すべてのデータをまとめてマスターテンプレートに投げる！
    print_html(
        "battle_layout_tmp.html",
        {
            "Conf": Conf,
            "token": session.get("token", ""),
            "action_logs": action_logs,
            "system_logs": system_logs,
            "menu_data": menu_data,
            "is_end": is_end,
        },
    )
