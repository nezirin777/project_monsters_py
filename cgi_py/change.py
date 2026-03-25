from sub_def.utils import error, print_html
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
    token = FORM["token"]

    party = open_party()

    # 入力取得（パーティ数に合わせる）
    c_no = [safe_int(FORM.get(f"c_no{i}")) for i in range(1, len(party) + 1)]

    # バリデーション
    validate_c_no(c_no, party)

    # 新しい並びを安全に構築（ロールバック前提）
    new_party = sorted(
        [{**pt, "no": c} for pt, c in zip(party, c_no)],
        key=lambda x: x["no"],
    )

    # 先頭モンスターの生存チェック
    if new_party[0]["hp"] == 0:
        error("No.1は必ず生存中のモンスターを設定をしてください")

    # 問題なければ保存
    save_party(new_party)

    content = {
        "Conf": Conf,
        "token": token,
        "mes": "並べ替えが完了しました",
    }

    print_html("result_tmp.html", content)
