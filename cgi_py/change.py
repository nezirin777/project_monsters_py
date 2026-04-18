# change.py -- パーティの並び替えを保存する関数
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

    if len(c_no) != len(party):
        error("並び替えデータ数が不正です")

    if any(n < 1 or n > len(party) for n in c_no):
        error("並び替えの数値が不正です")

    if len(c_no) != len(set(c_no)):
        error("並び替えの数値が重複しています")

    if set(c_no) != expected:
        error("並び替えの数値が不足しています")


def safe_int(val):
    try:
        return int(val)
    except (TypeError, ValueError):
        return 0


def change(FORM):
    """パーティの並び替えを保存する関数（user_all対応版）"""
    token = FORM["token"]

    # 新形式で全データを取得
    all_data = open_user_all()
    party = all_data.get("party", [])

    if not party:
        error("パーティデータがありません")

    # 1. フォームから送られてきた並び替え情報を取得
    c_no = []
    for i in range(1, len(party) + 1):
        val = FORM.get(f"c_no{i}")
        c_no.append(safe_int(val))

    # 2. バリデーション
    validate_c_no(c_no, party)

    # 3. 新しい並び順のパーティを作成
    new_party = [None] * len(party)

    for position, original_index in enumerate(c_no, 1):
        idx = original_index - 1
        if 0 <= idx < len(party):
            new_party[position - 1] = party[idx]

    if None in new_party:
        error("並び替えデータが不正です")

    # 4. ビジネスルールチェック：No.1は必ず生存中
    if new_party[0]["hp"] == 0:
        error("No.1は必ず生存中のモンスターを設定してください")

    # 5. 新しい位置に合わせて "no" を更新
    for new_no, monster in enumerate(new_party, 1):
        monster["no"] = new_no

    # 6. 保存（user_all経由）
    all_data["party"] = new_party
    save_user_all(all_data)

    success("並べ替えが完了しました。")
