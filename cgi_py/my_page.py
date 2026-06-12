# my_page.py - マイページ表示処理,ログイン後の基本画面。

import datetime
from typing import NoReturn

from sub_def.file_ops import (
    open_omiai_list,
    open_user_list,
    save_user_list,
    open_user_all,
    save_user_all,
)
from sub_def.utils import (
    error,
    print_html,
    slim_number_with_cookie,
    get_and_clear_flash,
)
from sub_def.user_ops import get_host

import conf

Conf = conf.Conf

_SKIP_MES: frozenset[str] = frozenset({"", "未登録"})


def calculate_costs_and_options(
    party: list,
) -> tuple[int, int, list[dict], list[dict]]:
    """宿屋・教会のコスト計算および配合・転換オプションを生成"""
    yadoya_cost = 0
    kyoukai_cost = 0
    haigou_options: list[dict] = []
    tenkan_options: list[dict] = []

    for i, pt in enumerate(party, 0):
        # 文字列の "0" などを考慮し、全て安全に数値化して扱う
        hp = int(pt.get("hp", 0))
        mhp = int(pt.get("mhp", 1))
        mp = int(pt.get("mp", 0))
        mmp = int(pt.get("mmp", 0))
        lv = int(pt.get("lv", 1))
        hai = int(pt.get("hai", 0))

        if hp != 0:
            yadoya_cost += (mhp - hp) + (mmp - mp)
        else:
            kyoukai_cost += (mhp + mmp) * 2

        if lv >= Conf["haigoulevel"]:
            haigou_options.append(
                {
                    "index": i,
                    "index_view": i + 1,
                    "name": pt.get("name", "不明"),
                    "sex": pt.get("sex", "不明"),
                    "lv": lv,
                    "hai": hai,
                }
            )

        if lv == 1:
            tenkan_options.append(
                {
                    "index": i,
                    "index_view": i + 1,
                    "name": pt.get("name", "不明"),
                    "sex": pt.get("sex", "不明"),
                    "cost": hai * 100,
                }
            )

    return yadoya_cost, kyoukai_cost, haigou_options, tenkan_options


def update_user_list(user_name: str, user: dict, party: list) -> None:
    """ユーザー一覧（グローバル）を更新"""
    u_list = open_user_list()
    bye = datetime.datetime.now() + datetime.timedelta(days=Conf["goodbye"])
    s = 3

    # party を最大3体までに整形。3体未満の場合は空辞書でパディングして
    # m1_name 〜 m3_name の全キーを確実に埋める
    display_party = party[:s] + [{} for _ in range(s - len(party))]

    # ユーザーがまだリストに存在しない場合の KeyError 対策
    if user_name not in u_list:
        u_list[user_name] = {}

    u_list[user_name] |= {
        "host": get_host(),
        "bye": bye.strftime("%Y-%m-%d"),
        "key": int(user.get("key") or 1),
        "money": int(user.get("money") or 0),
        "getm": user.get("getm", "0／0匹(0％)"),
        **{
            f"m{i+1}_{attr}": display_party[i].get(attr, "")
            for i in range(s)
            for attr in ["name", "lv", "hai"]
        },
    }
    save_user_list(u_list)


def get_recent_comments(u_list: dict, limit: int = 5) -> list[dict]:
    """
    user_list から有効なコメントを更新日時の新しい順に取得して返す。
    mes_updated_at がないエントリは最古扱い（ソート末尾）として含める。
    空・未登録コメントはスキップする。
    """
    entries = [
        {"name": name, "mes": u["mes"]}
        for name, u in u_list.items()
        if u.get("mes", "") not in _SKIP_MES
    ]
    entries.sort(
        key=lambda x: u_list[x["name"]].get("mes_updated_at", ""),
        reverse=True,
    )
    return entries[:limit]


def my_page(FORM: dict) -> NoReturn:
    """マイページ表示処理（user_all 完全対応版）"""
    session = FORM.get("s", {})

    # ユーザー名は FORM["s"] を優先して取得
    user_name = session.get("in_name")
    if not user_name:
        user_name = FORM.get("name")
    if not user_name:
        # 念のためエラー処理（通常はここには来ないはず）
        error("ユーザー名が取得できませんでした。", jump="top")

    token = session.get("token")

    # Flashメッセージの取得とクリア（一番最初に呼ぶ）
    flash_msg, flash_type = get_and_clear_flash(FORM["s"])

    # 空文字が来た場合の ValueError を防ぐため `or default` を使用
    try:
        last_floor = int(session.get("last_floor") or 1)
        last_floor_isekai = int(session.get("last_floor_isekai") or 0)
        next_t = float(session.get("next_t") or 0)
    except ValueError:
        last_floor = 1
        last_floor_isekai = 0
        next_t = 0.0

    last_room = session.get("last_room", "")

    omiai_list = open_omiai_list()

    all_data = open_user_all(user_name)

    user = all_data.get("user", {})
    party = all_data.get("party", [])
    vips = all_data.get("vips", {})
    room_key = all_data.get("room_key", {})
    waza = all_data.get("waza", {})

    # ユーザーリスト更新
    update_user_list(user_name, user, party)

    # 横スクロール用: 最新コメント5件を取得
    recent_comments = get_recent_comments(open_user_list(), 10)

    # ブーストの有効期限チェック
    now_ts = datetime.datetime.now().timestamp()
    boost_until = vips.get("boost")

    boost_flg = False
    boost_remain_sec = 0

    if boost_until is not None and boost_until > now_ts:
        boost_flg = True
        boost_remain_sec = int(boost_until - now_ts)
    elif boost_until is not None:
        # 期限切れ → Noneにリセットして保存
        vips["boost"] = None
        all_data["vips"] = vips
        save_user_all(all_data, user_name)

    hours = boost_remain_sec // 3600
    minutes = (boost_remain_sec % 3600) // 60
    seconds = boost_remain_sec % 60
    boost_time = f"{hours}時間{minutes}分{seconds}秒"

    # 追加情報生成 (ここも古いデータの空文字を考慮して int 化)
    isekai_limit = int(user.get("isekai_limit") or 0)
    isekai_key = int(user.get("isekai_key") or 0)

    if "isekai_clear" not in user:
        user["isekai_clear"] = max(0, isekai_key - 1)
        all_data["user"] = user
        save_user_all(all_data, user_name)

    # 異世界機能が未解放の場合は UI を非表示にする（isekai="hidden"）
    isekai, isekai_next = (
        ("hidden", "") if not isekai_limit else ("", min(isekai_key, isekai_limit))
    )

    park_get = "" if vips.get("パーク") else "hidden"

    # 表示用データ準備
    option_list = list(range(1, len(party) + 1))
    party_with_index = list(enumerate(slim_number_with_cookie(party), 1))
    user_v = slim_number_with_cookie(user)

    # 鍵の表示リスト
    room_key_display = [
        {
            "name": name,
            "has_key": int(r_key.get("get") or 0) == 1,
            "selected": (last_room == name),
        }
        for name, r_key in room_key.items()
    ]

    # 技の表示リスト
    waza_display = [
        {"name": name if int(wa.get("get") or 0) == 1 else "-"}
        for name, wa in waza.items()
    ]

    # お見合い状況
    omiai_status = (
        "baby"
        if omiai_list.get(user_name, {}).get("baby")
        else (
            "request"
            if any(user_name == omiai.get("request") for omiai in omiai_list.values())
            else ""
        )
    )

    # 宿屋・教会コスト計算
    yadoya_cost, kyoukai_cost, haigou_options, tenkan_options = (
        calculate_costs_and_options(party)
    )

    yadoya_cost_v = slim_number_with_cookie(yadoya_cost)
    kyoukai_cost_v = slim_number_with_cookie(kyoukai_cost)

    # テンプレートに渡すデータ
    content = {
        "my_page_flg": 1,
        "Conf": Conf,
        "user_name": user_name,
        "token": token,
        "next_t": next_t,
        "isekai": isekai,
        "isekai_next": isekai_next,
        "last_floor": last_floor,
        "last_floor_isekai": last_floor_isekai,
        "park_get": park_get,
        "user": user,
        "user_v": user_v,
        "boost_flg": boost_flg,
        "boost_time": boost_time,
        "party_with_index": party_with_index,
        "option_list": option_list,
        "room_key_display": room_key_display,
        "waza_display": waza_display,
        "omiai_status": omiai_status,
        "yadoya_cost": yadoya_cost,
        "kyoukai_cost": kyoukai_cost,
        "yadoya_cost_v": yadoya_cost_v,
        "kyoukai_cost_v": kyoukai_cost_v,
        "haigou_options": haigou_options,
        "tenkan_options": tenkan_options,
        "flash_msg": flash_msg,
        "flash_type": flash_type,
        "recent_comments": recent_comments,
        # my_page_myparty_tmp.html 内の図鑑リンクで {{ fol }} を参照するため明示的に渡す。
        # 自分のページは常に自分のフォルダを参照するため空文字固定。
        # （my_page2.py では FORM.get("fol", "") を渡している）
        "fol": "",
    }

    print_html("my_page_tmp.html", content)
