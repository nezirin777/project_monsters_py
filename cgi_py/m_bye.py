# m_bye.py - パーティからモンスターを削除し、新しいモンスターを追加する関数

from sub_def.file_ops import open_user_all, save_user_all, open_battle
from sub_def.monster_ops import monster_select
from sub_def.utils import error, success


def m_bye(FORM):
    # フォームの入力値を安全に取得（空文字や未送信による ValueError を防ぐ）
    try:
        # 仲間にしない場合はHTML側から "99" などが送られてくる想定
        Mno = int(FORM.get("Mno", 99))
    except ValueError:
        error("モンスターの選択が不正です", jump="my_page")

    user_name = FORM["s"].get("in_name")

    # user_all で全データを一括取得
    all_data = open_user_all(user_name)
    party = all_data.get("party", [])

    # battleデータを開く際に user_name を引数として渡す
    battle = open_battle(user_name)

    # バトルデータが破損・消失している場合のフェイルセーフ
    if not battle or not battle.get("teki"):
        error(
            "戦闘データが見つかりません。最初からやり直してください。", jump="my_page"
        )

    # teki[0] に仲間になるモンスター情報が入っている前提
    teki = battle["teki"][0]
    get_name = teki.get("name", "")
    Asex = teki.get("sex", "不明")  # sexキーがない場合の保険

    if not get_name:
        error("仲間にするモンスターの情報がありません。", jump="my_page")

    # メッセージの初期設定
    if Mno == 99:
        # Mnoが99（仲間にしない選択をした）場合
        message = f"<span>{get_name}</span>はさみしそうにさっていった"
    else:
        # そのまま配列のインデックス(0, 1, 2...)として使用する
        if Mno < 0 or Mno >= len(party):
            error("無効なモンスター番号が指定されました", jump="my_page")

        by_name = party[Mno].get("name", "不明")

        # 指定されたインデックスのモンスターを削除
        party.pop(Mno)

        # 新しいモンスターを追加
        new_mob = monster_select(get_name)
        new_mob["sex"] = Asex
        party.append(new_mob)

        # パーティ番号の再設定
        for i, pt in enumerate(party, 1):
            pt["no"] = i

        message = f"<span>{get_name}</span>が加わり<span>{by_name}</span>はさっていった"

    # 更新と結果表示（partyをuser_allに反映）
    all_data["party"] = party
    save_user_all(all_data, user_name)

    success(message, jump="my_page")
