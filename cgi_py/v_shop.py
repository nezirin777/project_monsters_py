# v_shop.py - VIPショップ モンスター交換処理

# 価格は購入回数に応じて上昇する（base_price × (1 + 購入回数)）
# 100vips = 50メダル, 10vips = 5メダル, 1vips = 0.5メダル

from sub_def.file_ops import open_vips_shop_dat, open_user_all, save_user_all
from sub_def.utils import error, success
from sub_def.monster_ops import monster_select
import conf

Conf = conf.Conf

# 購入キー名ごとの特殊初期値設定。
# monster_select() のデフォルト値を上書きしたいモンスターのみ定義する
_SPECIAL_SETTINGS: dict[str, dict] = {
    "スライム+100": {"hai": 100, "mlv": 100},
    "スライム+1000": {"hai": 1000, "mlv": 1000},
}


def _add_monster_to_party(party: list, monster_name: str, shop_key: str) -> None:
    """
    生成したモンスターをパーティに追加し、no を振り直す。

    Args:
        party       : 現在のパーティリスト（直接変更される）
        monster_name: マスターデータ上の実際のモンスター名（b_name）
        shop_key    : ショップの購入キー名。特殊設定の照合に使用する
    """
    if len(party) >= 10:
        error("モンスターが一杯です！", jump="my_page")
        # error() は NoReturn のためここには到達しない

    new_mob = monster_select(monster_name)

    # 特殊モンスターは初期値を上書きする（通常モンスターは空辞書なので何もしない）
    new_mob.update(_SPECIAL_SETTINGS.get(shop_key, {}))
    new_mob["lv"] = 1

    party.append(new_mob)
    for i, pt in enumerate(party, 1):
        pt["no"] = i


def v_shop_ok(FORM: dict) -> None:
    """VIPショップでのモンスター購入処理"""
    m_name = FORM.get("m_name")

    if not m_name:
        error("対象が選択されていません。", jump="v_shop")

    session = FORM.get("s", {})
    user_name = session.get("in_name")

    user_all = open_user_all(user_name)
    user = user_all.get("user", {})
    party = user_all.get("party", [])
    vips = user_all.get("vips", {})

    vshop_list = open_vips_shop_dat()

    # 不正な m_name（画面改ざん等）への対策
    item = vshop_list.get(m_name)
    if not item:
        error("指定されたモンスターが存在しません。", jump="v_shop")

    # b_name が設定されていない場合は購入キー名をそのままモンスター名として使う
    Aname = item.get("b_name", m_name)
    base_price = int(item.get("price", 0))

    # 購入回数に応じて価格が上昇する（base × (1 + 購入回数)）
    price = base_price + base_price * int(vips.get(m_name, 0))

    # 通貨種別の判定と残高チェック
    currency = "medal" if item.get("type") == "メダル" else "money"
    if int(user.get(currency, 0)) < price:
        error(f"{item.get('type', '資金')}が足りません！", jump="my_page")

    # 通貨を消費してパーティに追加
    user[currency] = int(user.get(currency, 0)) - price
    _add_monster_to_party(party, Aname, m_name)

    # 購入回数を更新（次回以降の価格計算に使用）
    vips[m_name] = int(vips.get(m_name, 0)) + 1

    user_all["user"] = user
    user_all["party"] = party
    user_all["vips"] = vips
    save_user_all(user_all, user_name)

    success(f"【{Aname}】が仲間に加わりました！", jump="v_shop")
