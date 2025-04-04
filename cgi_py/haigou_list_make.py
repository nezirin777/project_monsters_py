from jinja2 import Environment, FileSystemLoader
import sys
import sub_def
import conf

Conf = conf.Conf
sys.stdout.reconfigure(encoding="utf-8")


def haigou_list_make():
    # list(通常モンスタ)用

    M_types = [
        "スライム系",
        "ドラゴン系",
        "けもの系",
        "とり系",
        "しょくぶつ系",
        "むし系",
        "あくま系",
        "ゾンビ系",
        "ぶっしつ系",
        "みず系",
        "？？？系",
    ]

    # 表示させないモンスター
    M_del_list = [
        "アイぼう",
        "かくれんぼう",
        "じげんりゅう",
        "ラーミア",
        "ゾーマズデビル",
        "マスタードラゴン",
    ]

    M_list = sub_def.open_monster_dat()

    # フィルタリングされたモンスターリストを作成
    filtered_M_list = {
        m_type: {
            name: dat
            for name, dat in M_list.items()
            if dat["m_type"] == m_type and name not in M_del_list
        }
        for m_type in M_types
    }

    # リンク用のデータ作成
    links = [{"id": m_type, "label": m_type} for m_type in M_types]

    context1 = {
        "Conf": Conf,
        "links": links,
        "filtered_M_list": filtered_M_list,
    }

    # Jinja2テンプレート環境を設定
    env = Environment(loader=FileSystemLoader("templates"), cache_size=100)
    template1 = env.get_template("haigou_list_tmp.html")

    # テンプレートをレンダリング
    html1 = template1.render(context1)
    footer_html = sub_def.footer_temp()

    # HTMLとフッターを結合
    combined_html1 = html1 + footer_html

    # ファイル保存 (haigou_list.html)
    output_path1 = "html/haigou_list.html"
    with open(output_path1, "w", encoding="utf-8") as file:
        file.write(combined_html1)

    # 以下list2(特殊モンスタ)用

    monsters = [
        {
            "name": name,
            "m_type": data["m_type"],
            "floor_min": data["階層A"],
            "floor_max": data["階層B"],
            "description_a": data["説明A"],
            "description_b": data["説明B"],
            "hp": data["hp"],
            "mp": data["mp"],
            "atk": data["atk"],
            "def": data["def"],
            "agi": data["agi"],
            "exp": data["exp"],
            "money": data["money"],
            "date": data["date"],
            "no": data["no"],
        }
        for name, data in M_list.items()
        if data["room"] == "特殊"
    ]

    context2 = {
        "Conf": Conf,
        "monsters": monsters,
    }

    # Jinja2テンプレート環境を設定
    template2 = env.get_template("haigou_list2_tmp.html")

    # テンプレートをレンダリング
    html2 = template2.render(context2)

    # HTMLとフッターを結合
    combined_html2 = html2 + footer_html

    # ファイル保存
    output_path = "html/haigou_list2.html"
    with open(output_path, "w", encoding="utf-8") as file:
        file.write(combined_html2)
