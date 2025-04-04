def tournament_result(FORM):
    import os
    import sub_def
    import conf

    Conf = conf.Conf
    log = os.path.join(Conf["savedir"], "tournament.log")

    try:
        # トーナメントログファイルの確認と作成
        if not os.path.exists(log):
            with open(log, mode="w", encoding="utf-8") as f:
                f.write("""<div class="medal_battle_title">まだ未開催です</div>""")

        # ファイルの読み込み
        with open(log, mode="r", encoding="utf-8") as f:
            html = f.read()

    except IOError as e:
        sub_def.error(
            f"トーナメントログファイルの読み込み中にエラーが発生しました: {e}"
        )

    sub_def.header()
    print(html)
    sub_def.footer()
