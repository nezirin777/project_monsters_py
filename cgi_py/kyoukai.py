# kyoukai.py - 教会でのお祈り処理

from sub_def.file_ops import open_user_all, save_user_all
from sub_def.utils import error, success


def recover_monster(monster):
    """モンスターのHP・MPを回復し、回復コストを計算"""

    # 古い仕様による文字列の "0" などを考慮し、安全に数値化して判定
    if int(monster.get("hp", 0)) == 0:

        # キーが存在しない場合(KeyError)のクラッシュを防ぐため get を使用
        mhp = int(monster.get("mhp", 1))
        mmp = int(monster.get("mmp", 0))

        # HP・MPを最大値まで回復
        monster["hp"] = mhp
        monster["mp"] = mmp

        # コスト計算: (最大HP + 最大MP) * 2
        return (mhp + mmp) * 2

    return 0


def kyoukai(FORM):
    """お祈りによりパーティのHP・MPを回復し、費用を更新（user_all対応）"""

    # セッション切れ等でのクラッシュ対策
    try:
        user_name = FORM["s"]["in_name"]
    except KeyError:
        error("セッション情報が不正です", jump="top")

    # user_all で全データを一括取得
    all_data = open_user_all(user_name)
    user = all_data.get("user", {})
    party = all_data.get("party", [])

    # 回復処理と費用計算
    # ※ recover_monster 内で pt(辞書) が直接書き換えられます。
    # 仮にこの後の残高チェックでエラーになっても、save_user_all が走らなければ
    # データは保存されないため、このタイミングでの書き換えは安全です。
    total_cost = sum(recover_monster(pt) for pt in party)

    # エラーチェック
    if total_cost == 0:
        error("現在お祈りする必要はありません", jump="my_page")

    # moneyキーがない場合の KeyError を防ぐ
    if int(user.get("money", 0)) < total_cost:
        error("お金が足りません", jump="my_page")

    # 所持金更新
    user["money"] = int(user.get("money", 0)) - int(total_cost)

    # user_all に反映して保存（partyも含めて1回で保存）
    all_data["user"] = user
    all_data["party"] = party
    save_user_all(all_data, user_name)

    success("お祈りが天にとどきました", jump="my_page")
