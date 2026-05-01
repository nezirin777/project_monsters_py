from sub_def.file_ops import open_user_all, save_user_all
from sub_def.utils import error, success
import conf

Conf = conf.Conf


def seitenkan_ok(FORM):
    user_name = FORM["s"]["in_name"]
    # 配列位置に合わせるため-1
    no = int(FORM["no"]) - 1

    all_data = open_user_all(user_name)
    user = all_data.setdefault("user", {})
    party = all_data.setdefault("party", [])

    # 範囲チェック
    if no < 0 or no >= len(party):
        error("選択された対象が無効です。", jump="my_page")

    pt = party[no]
    cost = pt.get("hai", 0) * 100

    # お金チェック（旧seitenkanから移動）
    if user.get("money", 0) < cost:
        error("お金が足りません", jump="my_page")

    # 性別変換処理
    sexs = Conf["sex"]
    current_sex = pt.get("sex")

    if current_sex in sexs:
        pt["sex"] = sexs[(sexs.index(current_sex) + 1) % len(sexs)]
    else:
        # 万が一設定ファイルにない性別だった場合の安全策
        pt["sex"] = sexs[0]

    # 料金支払い
    user["money"] -= cost

    # 保存
    all_data["user"] = user
    all_data["party"] = party
    save_user_all(all_data, user_name)

    success(f"{pt['name']}の陰陽転換が完了しました。", jump="my_page")
