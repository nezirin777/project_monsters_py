# seitenkan_ok.py - 陰陽転換（性別変更）処理

from sub_def.file_ops import open_user_all, save_user_all
from sub_def.utils import error, success
import conf

Conf = conf.Conf


def seitenkan_ok(FORM):
    # セッション切れによる KeyError を防ぐための安全な取得
    session = FORM.get("s", {})
    user_name = session.get("in_name")

    if not user_name:
        error("セッション情報が不正です。", jump="top")

    # フォームの入力値を安全に取得（空文字や未送信による ValueError を防ぐ）
    try:
        # マイページ側で未選択の場合は 99 が送られてくる想定
        no = int(FORM.get("no", 99))
    except ValueError:
        error("対象が正しく選択されていません。", jump="my_page")

    # 未選択エラーのハンドリング
    if no == 99:
        error("陰陽転換するモンスターを選択してください。", jump="my_page")

    all_data = open_user_all(user_name)

    # setdefaultも良いですが、他のファイルと統一してgetを使用（欠損時のクラッシュ防止）
    user = all_data.get("user", {})
    party = all_data.get("party", [])

    # 範囲チェック（指定されたインデックスがパーティ内に存在するか）
    if no < 0 or no >= len(party):
        error("選択された対象が無効です。", jump="my_page")

    pt = party[no]
    cost = int(pt.get("hai", 0)) * 100

    # お金チェック
    if int(user.get("money", 0)) < cost:
        error("お金が足りません", jump="my_page")

    # 性別変換処理
    sexs = Conf.get("sex", ["陽", "陰"])  # 万が一Confに未定義だった場合の保険
    current_sex = pt.get("sex")

    # 現在の性別の次の性別へ（配列の最後まで行ったら最初に戻るスマートな処理）
    if current_sex in sexs:
        pt["sex"] = sexs[(sexs.index(current_sex) + 1) % len(sexs)]
    else:
        # 万が一設定ファイルにない性別だった場合の安全策
        pt["sex"] = sexs[0]

    # 料金支払い
    user["money"] = int(user.get("money", 0)) - cost

    # 保存
    all_data["user"] = user
    all_data["party"] = party
    save_user_all(all_data, user_name)

    success(f"{pt.get('name', '不明')}の陰陽転換が完了しました。", jump="my_page")
