import sub_def


def validate_c_no(c_no, party):
    """並べ替えの重複や不正値をチェック"""
    unique_c_no = set(c_no)
    # 0がある分-1
    if len(party) != len(unique_c_no) - 1:
        sub_def.error("並び替えの数値が重複しています")


def change(FORM):

    c_no = [int(FORM.get(f"c_no{i}", 0)) for i in range(1, 11)]
    c_no.append(0)  # 10体埋まっているときに末尾に0を追加

    party = sub_def.open_party()

    # 並べ替えのエラーチェック
    validate_c_no(c_no, party)

    # モンスター番号を更新
    for pt, c in zip(party, c_no):
        pt["no"] = c
    party.sort(key=lambda x: x["no"])

    # 先頭モンスターが生存中か確認
    if party[0]["hp"] == 0:
        sub_def.error("No.1は必ず生存中のモンスターを設定をしてください")

    sub_def.save_party(party)

    sub_def.result("並べ替えが完了しました", "", FORM["token"])
