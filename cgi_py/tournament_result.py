# tournament_result.py - トーナメント結果表示

import os
from sub_def.utils import error, print_html
import conf

Conf = conf.Conf


def tournament_result(FORM):
    log_path = os.path.join(Conf["savedir"], "tournament.log")

    try:
        # トーナメントログファイルの確認と作成
        if not os.path.exists(log_path):
            with open(log_path, mode="w", encoding="utf-8") as f:
                f.write("""<div class="medal_battle_title">まだ未開催です</div>""")

        # ファイルの読み込み
        with open(log_path, mode="r", encoding="utf-8") as f:
            html_content = f.read()

    except IOError as e:
        error(
            f"トーナメントログファイルの読み込み中にエラーが発生しました: {e}",
            jump="top",
        )

    # テンプレートへ渡すデータ
    content = {
        "Conf": Conf,
        "tournament_html": html_content,
    }

    # Jinja2テンプレートで描画
    print_html("tournament_result_tmp.html", content)
