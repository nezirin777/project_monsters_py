# haigou_list_make.py - 配合モンスターリストの生成

from jinja2 import Environment, FileSystemLoader

from sub_def.monster_ops import (
    open_monster_dat,
)
import conf

Conf = conf.Conf

# Jinja2テンプレート環境を設定
env = Environment(loader=FileSystemLoader("templates"))


def build_monster_view(name, data):
    return {
        "name": name,
        "no": data.get("no", 0),
        "m_type": data.get("m_type", ""),
        "blood": [data.get(f"血統{i}") for i in range(1, 4) if data.get(f"血統{i}")],
        "mate": [data.get(f"相手{i}") for i in range(1, 4) if data.get(f"相手{i}")],
        "floor": build_floor(data.get("階層A"), data.get("階層B")),
        "get_text": "OK" if data.get("get") else "NO",
    }


def build_floor(a, b):
    if not a:
        return ""
    if b:
        return f"{a}階～{b}階"
    return f"{a}階～"


def normalize_monster(m):
    return {
        "name": m["name"],
        "m_type": m.get("m_type", ""),
        "floor": build_floor(m.get("floor_min"), m.get("floor_max")),
        "room": m.get("room", ""),
        "desc_a": m.get("description_a", ""),
        "desc_b": m.get("description_b", ""),
        "stats": f'HP:{m["hp"]} MP:{m["mp"]} ATK:{m["atk"]} DEF:{m["def"]} AGI:{m["agi"]} EXP:{m["exp"]} MONEY:{m["money"]}',
        "date": m.get("date", ""),
        "no": m.get("no", 0),
        "floor_min": m.get("floor_min", 0),
    }


# list2用（normalize前データ生成）
def build_list2(M_list):
    result = []

    for name, data in M_list.items():
        if int(data.get("list_type") or 0) == 2:

            is_hidden = int(data.get("name_hidden") or 0) == 1
            description_a = (
                f"<span>{data.get('説明A', '')}</span>"
                if int(data.get("omiai_only") or 0) == 1
                else data.get("説明A", "")
            )

            result.append(
                {
                    "name": "？？？" if is_hidden else name,
                    "m_type": data.get("m_type", ""),
                    "floor_min": data.get("階層A", ""),
                    "floor_max": data.get("階層B", ""),
                    "room": data.get("room", "出現しない"),
                    "description_a": description_a,
                    "description_b": data.get("説明B", ""),
                    "hp": data.get("hp", 0),
                    "mp": data.get("mp", 0),
                    "atk": data.get("atk", 0),
                    "def": data.get("def", 0),
                    "agi": data.get("agi", 0),
                    "exp": data.get("exp", 0),
                    "money": data.get("money", 0),
                    "date": data.get("date", "2000/1/1"),
                    "no": data.get("no", 0),
                }
            )

    return result


def haigou_list_make():
    M_list = open_monster_dat()

    # =========================
    # list1（通常モンスター）
    # =========================

    filtered_M_list = {}

    for name, dat in M_list.items():
        # 判定はこれだけ
        if int(dat.get("list_type") or 0) == 2:
            continue

        m_type = dat.get("m_type", "その他")

        monster = build_monster_view(name, dat)

        # グループ初期化
        if m_type not in filtered_M_list:
            filtered_M_list[m_type] = []

        filtered_M_list[m_type].append(monster)

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

    # リンク用のデータ作成
    links = [{"id": m_type, "label": m_type} for m_type in M_types]

    context1 = {
        "Conf": Conf,
        "filtered_M_list": filtered_M_list,
        "links": links,
    }

    template1 = env.get_template("haigou_list_tmp.html")

    html1 = template1.render(context1)

    with open("html/haigou_list.html", "w", encoding="utf-8") as file:
        file.write(html1)

    # =========================
    # list2（特殊モンスター）
    # =========================

    monsters_raw = build_list2(M_list)
    monsters = [normalize_monster(m) for m in monsters_raw]

    seen = set()
    links2 = []

    for m in monsters:
        t = m["m_type"]
        if t and t not in seen:
            seen.add(t)
            links2.append({"id": t, "label": t})

    context2 = {
        "Conf": Conf,
        "monsters": monsters,
        "links": links2,
    }

    template2 = env.get_template("haigou_list2_tmp.html")

    html2 = template2.render(context2)

    with open("html/haigou_list2.html", "w", encoding="utf-8") as file:
        file.write(html2)
