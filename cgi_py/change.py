# change.py パーティの並び替えを保存する関数

from sub_def.utils import error, success
from sub_def.file_ops import (
    open_user_all,
    save_user_all,
)
import conf

Conf = conf.Conf


def validate_c_no(c_no, party):
    """並び替えの重複・欠損・範囲チェック"""
    expected = set(range(1, len(party) + 1))

    # フォームからの送信データ数と実際のパーティ数が一致しているか
    if len(c_no) != len(party):
        error("並び替えデータ数が不正です", jump="my_page")

    # 1〜パーティ数の範囲外の数値が混ざっていないか
    if any(n < 1 or n > len(party) for n in c_no):
        error("並び替えの数値が不正です", jump="my_page")

    # 同じ番号が複数指定されていないか（重複チェック）
    if len(c_no) != len(set(c_no)):
        error("並び替えの数値が重複しています", jump="my_page")

    # 1〜パーティ数までの数値が過不足なく全て揃っているか
    if set(c_no) != expected:
        error("並び替えの数値が不足しています", jump="my_page")


def safe_int(val):
    """安全な数値変換（空文字やNoneが来た場合もクラッシュさせない）"""
    try:
        return int(val)
    except (TypeError, ValueError):
        return 0


def change(FORM):
    """パーティの並び替えを保存する関数（user_all対応版）"""
    user_name = FORM["s"]["in_name"]

    # 新形式で全データを取得
    all_data = open_user_all(user_name)
    party = all_data.get("party", [])

    # パーティが存在しない場合のフェイルセーフ
    if not party:
        error("パーティデータがありません", jump="top")

    # 1. フォームから送られてきた並び替え情報を取得
    # （例: c_no1=3, c_no2=1, c_no3=2 といった値を取り出してリスト化する）
    c_no = []
    for i in range(1, len(party) + 1):
        val = FORM.get(f"c_no{i}")
        c_no.append(safe_int(val))

    # 2. バリデーション（不正な値がないか厳密にチェック）
    validate_c_no(c_no, party)

    # 3. 新しい並び順のパーティを作成
    new_party = [None] * len(party)

    # 指定された順番通りに新しい配列へモンスターを格納していく
    for position, original_index in enumerate(c_no, 1):
        idx = original_index - 1
        if 0 <= idx < len(party):
            new_party[position - 1] = party[idx]

    # 万が一、格納漏れ（None）が発生した場合は安全のため弾く
    if None in new_party:
        error("並び替えデータが不正です", jump="my_page")

    # 4. ビジネスルールチェック：No.1は必ず生存中
    # ※古い仕様でhpが文字列の"0"になっている可能性も考慮してint()で安全に判定
    if int(new_party[0].get("hp", 0)) == 0:
        error("No.1は必ず生存中のモンスターを設定してください", jump="my_page")

    # 5. 新しい位置に合わせて "no" を更新
    for new_no, monster in enumerate(new_party, 1):
        monster["no"] = new_no

    # 6. 保存（user_all経由）
    all_data["party"] = new_party
    save_user_all(all_data, user_name)

    success("並べ替えが完了しました。", jump="my_page")
