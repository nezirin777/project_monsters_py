from jinja2 import Environment, FileSystemLoader
import sub_def
import conf

Conf = conf.Conf


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

    # ファイル保存 (haigou_list.html)
    output_path1 = "html/haigou_list.html"
    with open(output_path1, "w", encoding="utf-8") as file:
        file.write(html1)

    # 以下list2(特殊モンスタ)用
    monsters1 = [
        {
            "name": "ワンダーエッグ",
            "floor_min": "",
            "floor_max": "",
            "room": "出現しない",
            "description_a": "<span>？？？</span>",
            "description_b": "<span>？？？</span>",
            "hp": 10,
            "mp": 3,
            "atk": 5,
            "def": 8,
            "agi": 4,
            "exp": 10,
            "money": 100,
            "date": "2000/01/01",
            "m_type": "ワンダーエッグ",
        },
        {
            "name": "？？？",
            "floor_min": "",
            "floor_max": "",
            "room": "出現しない",
            "description_a": "<span>某精霊×某精霊(逆でもおｋ)</span>",
            "hp": 40,
            "mp": 60,
            "atk": 40,
            "def": 40,
            "agi": 80,
            "date": "2000/01/01",
            "m_type": "某精霊",
        },
        {
            "name": "？？？",
            "floor_min": "",
            "floor_max": "",
            "room": "出現しない",
            "description_a": "<span>相棒×たまご(逆でもおｋ)</span>",
            "hp": 50,
            "mp": 70,
            "atk": 50,
            "def": 50,
            "agi": 50,
            "date": "2000/01/01",
            "m_type": "相棒",
        },
        {
            "name": "？？？",
            "floor_min": "",
            "floor_max": "",
            "room": "出現しない",
            "description_a": "<span>真りゅうおう×隠(逆でもおｋ)</span>",
            "hp": 80,
            "mp": 60,
            "atk": 100,
            "def": 80,
            "agi": 90,
            "date": "2000/01/01",
            "m_type": "真りゅうおう",
        },
        {
            "name": "？？？",
            "floor_min": "",
            "floor_max": "",
            "room": "出現しない",
            "description_a": "<span>最強の鳥さん×↑(逆でもおｋ)</span>",
            "hp": 100,
            "mp": 100,
            "atk": 100,
            "def": 100,
            "agi": 100,
            "date": "2000/01/01",
            "m_type": "最強の鳥さん",
        },
        {
            "name": "？？？",
            "floor_min": "",
            "floor_max": "",
            "room": "出現しない",
            "description_a": "<span>アスラン×これでもラスボスでした。(逆でもおｋ)</span>",
            "hp": 50,
            "mp": 40,
            "atk": 60,
            "def": 40,
            "agi": 30,
            "date": "2000/01/01",
            "m_type": "アスラン",
        },
        {
            "name": "？？？",
            "floor_min": "",
            "floor_max": "",
            "room": "出現しない",
            "description_a": "<span>天界獣×ギスヴァーグ(逆でもおｋ)</span>",
            "hp": 150,
            "mp": 150,
            "atk": 150,
            "def": 150,
            "agi": 150,
            "date": "2000/01/01",
            "m_type": "天界獣",
        },
        {
            "name": "ひのせいれい",
            "floor_min": 300,
            "floor_max": "",
            "room": "通常部屋",
            "description_a": "交換所のみ",
            "hp": 25,
            "mp": 20,
            "atk": 30,
            "def": 10,
            "agi": 20,
            "exp": 300,
            "money": 300,
            "date": "2000/01/01",
            "m_type": "ひのせいれい",
        },
        {
            "name": "みずのせいれい",
            "floor_min": 300,
            "floor_max": "",
            "room": "通常部屋",
            "description_a": "交換所のみ",
            "hp": 20,
            "mp": 20,
            "atk": 20,
            "def": 20,
            "agi": 20,
            "exp": 300,
            "money": 300,
            "date": "2000/01/01",
            "m_type": "みずのせいれい",
        },
        {
            "name": "かぜのせいれい",
            "floor_min": 300,
            "floor_max": "",
            "room": "通常部屋",
            "description_a": "交換所のみ",
            "hp": 15,
            "mp": 20,
            "atk": 20,
            "def": 15,
            "agi": 30,
            "exp": 300,
            "money": 300,
            "date": "2000/01/01",
            "m_type": "かぜのせいれい",
        },
        {
            "name": "ちのせいれい",
            "floor_min": 300,
            "floor_max": "",
            "room": "通常部屋",
            "description_a": "交換所のみ",
            "hp": 30,
            "mp": 10,
            "atk": 25,
            "def": 30,
            "agi": 10,
            "exp": 300,
            "money": 300,
            "date": "2000/01/01",
            "m_type": "ちのせいれい",
        },
        {
            "name": "ひかりのせいれい",
            "floor_min": 300,
            "floor_max": "",
            "room": "通常部屋",
            "description_a": "ちのせいれい×みずのせいれい(逆でもok)",
            "hp": 30,
            "mp": 30,
            "atk": 30,
            "def": 30,
            "agi": 30,
            "exp": 400,
            "money": 200,
            "date": "2000/01/01",
            "m_type": "ひかりのせいれい",
        },
        {
            "name": "やみのせいれい",
            "floor_min": 300,
            "floor_max": "",
            "room": "通常部屋",
            "description_a": "ひのせいれい×かぜのせいれい(逆でもok)",
            "hp": 30,
            "mp": 30,
            "atk": 30,
            "def": 30,
            "agi": 30,
            "exp": 400,
            "money": 200,
            "date": "2000/01/01",
            "m_type": "やみのせいれい",
        },
        {
            "name": "イイロ",
            "floor_min": 400,
            "floor_max": "",
            "room": "通常部屋",
            "description_a": "スライム系×ちのせいれい",
            "hp": 5,
            "mp": 5,
            "atk": 7,
            "def": 6,
            "agi": 5,
            "exp": 100,
            "money": 100,
            "date": "2000/01/01",
            "m_type": "イイロ",
        },
        {
            "name": "ピモ",
            "floor_min": 400,
            "floor_max": "",
            "room": "通常部屋",
            "description_a": "スライム系×ひのせいれい",
            "hp": 6,
            "mp": 6,
            "atk": 5,
            "def": 7,
            "agi": 5,
            "exp": 100,
            "money": 100,
            "date": "2000/01/01",
            "m_type": "ピモ",
        },
        {
            "name": "アルー",
            "floor_min": 400,
            "floor_max": "",
            "room": "通常部屋",
            "description_a": "スライム系×みずのせいれい",
            "hp": 7,
            "mp": 4,
            "atk": 8,
            "def": 3,
            "agi": 5,
            "exp": 100,
            "money": 100,
            "date": "2000/01/01",
            "m_type": "アルー",
        },
        {
            "name": "ドリーン",
            "floor_min": 400,
            "floor_max": "",
            "room": "通常部屋",
            "description_a": "スライム系×かぜのせいれい",
            "hp": 8,
            "mp": 4,
            "atk": 4,
            "def": 5,
            "agi": 5,
            "exp": 100,
            "money": 100,
            "date": "2000/01/01",
            "m_type": "ドリーン",
        },
        {
            "name": "パーラル",
            "floor_min": 400,
            "floor_max": "",
            "room": "通常部屋",
            "description_a": "スライム系×やみのせいれい",
            "hp": 9,
            "mp": 5,
            "atk": 10,
            "def": 7,
            "agi": 5,
            "exp": 100,
            "money": 100,
            "date": "2000/01/01",
            "m_type": "パーラル",
        },
    ]

    monsters2 = [
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
            "room": "異世界",
        }
        for name, data in M_list.items()
        if data["room"] == "特殊"
    ]

    context2 = {
        "Conf": Conf,
        "monsters": monsters1 + monsters2,
    }

    # Jinja2テンプレート環境を設定
    template2 = env.get_template("haigou_list2_tmp.html")

    # テンプレートをレンダリング
    html2 = template2.render(context2)

    # ファイル保存
    output_path = "html/haigou_list2.html"
    with open(output_path, "w", encoding="utf-8") as file:
        file.write(html2)
