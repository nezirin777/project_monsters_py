from sub_def.utils import error, success
from sub_def.file_ops import open_party, save_party
import conf

Conf = conf.Conf


def validate_c_no(c_no, party):
    """並び替えの重複・欠損・範囲チェック"""
    expected = set(range(1, len(party) + 1))

    # 長さチェック（zip事故防止）
    if len(c_no) != len(party):
        error("並び替えデータ数が不正です")

    # 範囲チェック
    if any(n < 1 or n > len(party) for n in c_no):
        error("並び替えの数値が不正です")

    # 重複チェック
    if len(c_no) != len(set(c_no)):
        error("並び替えの数値が重複しています")

    # 欠損チェック（念のため）
    if set(c_no) != expected:
        error("並び替えの数値が不足しています")


def safe_int(val):
    try:
        return int(val)
    except (TypeError, ValueError):
        return 0


def change(FORM):
    """パーティの並び替えを保存する関数
    JavaScript側から送られてくる c_no1, c_no2, ... の値は
    「新しい位置に配置したいモンスターの、本来の番号」を意味しています。
    """
    token = FORM["token"]

    party = open_party()

    # 1. フォームから送られてきた並び替え情報を取得
    # c_no = [新しい1番目に置きたいモンスターの元番号,
    #         新しい2番目に置きたいモンスターの元番号, ...]

    c_no = []
    for i in range(1, len(party) + 1):
        val = FORM.get(f"c_no{i}")
        c_no.append(safe_int(val))

    # 2. バリデーション（不正な並び替えを防ぐ）
    validate_c_no(c_no, party)

    # 3. 新しい並び順のパーティを作成
    # new_party は「最終的に保存する新しい順番のリスト」
    new_party = [None] * len(party)

    for position, original_index in enumerate(c_no, 1):
        # c_noの値は1始まりなので、リストのインデックスにするために -1 する
        idx = original_index - 1

        # 安全策：範囲外の値が来てもエラーにしないようチェック
        if 0 <= idx < len(party):
            # 元のpartyから該当するモンスターを取り出して、新しい位置に配置
            new_party[position - 1] = party[idx]

    # Noneが残っていないか最終チェック（理論上は起きないはず）
    if None in new_party:
        error("並び替えデータが不正です")

    # 4. 追加のビジネスルールチェック
    # No.1（戦闘で先頭に立つモンスター）は必ず生きている必要がある
    if new_party[0]["hp"] == 0:
        error("No.1は必ず生存中のモンスターを設定してください")

    # 5. 新しい位置に合わせて各モンスターの "no" を更新
    for new_no, monster in enumerate(new_party, 1):
        monster["no"] = new_no

    # 6. 保存
    save_party(new_party)
    success("並べ替えが完了しました。")
