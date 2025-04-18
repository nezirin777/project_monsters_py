import time
import sub_def
import conf
import cgi_py

Conf = conf.Conf


def initialize_battle(FORM):
    in_floor = int(FORM["c"].get("last_floor", 0))
    if in_floor == 0:
        sub_def.error("階層選択がおかしいです？")

    special = FORM["c"]["special"]
    turn = int(FORM["c"]["turn"])

    return in_floor, special, turn


def next_turn_setup(FORM, turn):
    next_t = time.time() + Conf["nextplay"]  # エポック秒
    FORM["c"] |= {"next_t": next_t, "turn": turn + 1}
    sub_def.set_cookie(FORM["c"])


def setup_battle_data(special):
    battle = sub_def.open_battle()
    pt_num = min(len(battle["party"]), 3)
    if special in ("わたぼう", "スライム"):
        pt_num = 1
    return battle, pt_num


def prepare_battle_commands(FORM, party):
    bt = [
        {
            "hit": FORM.get("hit1", 0),
            "target": int(FORM.get("target1", 0)),
            "toku": FORM.get("toku1", 0),
            "nakama": int(FORM.get("nakama1", 0)),
            "ktoku": FORM.get("ktoku1", 0),
        },
        {
            "hit": FORM.get("hit2", 0),
            "target": int(FORM.get("target2", 0)),
            "toku": FORM.get("toku2", 0),
            "nakama": int(FORM.get("nakama2", 0)),
            "ktoku": FORM.get("ktoku2", 0),
        },
        {
            "hit": FORM.get("hit3", 0),
            "target": int(FORM.get("target3", 0)),
            "toku": FORM.get("toku3", 0),
            "nakama": int(FORM.get("nakama3", 0)),
            "ktoku": FORM.get("ktoku3", 0),
        },
    ]
    for pt, b in zip(party, bt):
        pt["bt"] = b
    return bt


def execute_battle_actions(BT, battle, special, in_floor):
    for bt in BT:
        if bt.get("no"):
            bt["休み"] = 0

    for bt in BT:
        if bt["hp"] > 0 and bt.get("休み", 0) == 0:
            if bt.get("no"):
                battle = cgi_py.battle_action.mikata_action(bt, battle)
            else:
                battle = cgi_py.battle_action.teki_action(bt, battle, special, in_floor)


def handle_battle_end_conditions(FORM, battle, pt_num, special, in_floor, turn):

    if battle["teki"][0]["down"] == len(battle["teki"]):

        cgi_py.battle_sub.battle_end("勝利した", 1, special)
        if special == 0:
            cgi_py.battle_sub.key_get(in_floor)
            cgi_py.battle_sub.mon_get(FORM)
        elif special == "スライム":  # スライム城
            cgi_py.battle_sub.battle_roomkey_get(FORM["token"])
        elif special == "わたぼう":  # わたぼう城
            cgi_py.battle_sub.battle_medal_get(in_floor)
        elif special == "vipsg":
            cgi_py.battle_sub.battle_isekai_limit_get()
        elif special == "異世界":
            cgi_py.battle_sub.battle_isekai_key_get(
                int(FORM["c"].get("last_floor_isekai", 0))
            )
            cgi_py.battle_sub.mon_get(FORM)
        sub_def.my_page_button(FORM["token"])

    elif pt_num == len([1 for pt in battle["party"] if pt["hp"] == 0]):
        cgi_py.battle_sub.battle_end("負けた", 0, special)
        if special == 0 or special == "異世界":
            cgi_py.battle_sub.haisen()
        sub_def.my_page_button(FORM["token"])

    elif turn >= Conf["maxround"]:
        cgi_py.battle_sub.battle_end("引き分けた", 0.5, special)
        sub_def.my_page_button(FORM["token"])


def battle_fight(FORM):

    # 初期化と入力バリデーション
    in_floor, special, turn = initialize_battle(FORM)
    if in_floor is None:
        return

    next_turn_setup(FORM, turn)

    # バトルデータの取得と準備
    battle, pt_num = setup_battle_data(special)
    prepare_battle_commands(FORM, battle["party"])

    # 行動順を決定
    BT = sorted(
        battle["party"] + battle["teki"][1:], key=lambda x: x["agi"], reverse=True
    )

    sub_def.header()

    # 各キャラクターの行動を実行
    execute_battle_actions(BT, battle, special, in_floor)

    for pt in battle["party"]:
        del pt["bt"]
        del pt["休み"]

    sub_def.save_battle(battle)

    # 行動後の後処理と戦闘の継続判定
    handle_battle_end_conditions(FORM, battle, pt_num, special, in_floor, turn)

    if special != "わたぼう" and special != "スライム":
        txt = cgi_py.battle_menu.battle_menu(FORM, special)
        print(txt)
        sub_def.footer()
    else:
        txt = cgi_py.battle_menu.battle_menu(FORM, special)
        print(txt)
        sub_def.footer()
