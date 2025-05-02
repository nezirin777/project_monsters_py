import sys
import secrets
import logging
from jinja2 import Environment, FileSystemLoader

import conf

sys.stdout.reconfigure(encoding="utf-8")
sys.stdin.reconfigure(encoding="utf-8")

Conf = conf.Conf

# ログ設定（UTF-8で保存）
logging.basicConfig(
    filename="app.log",
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8",
)

env = Environment(loader=FileSystemLoader("templates"))


# ========#
# エラー  #
# ========#
def error(txt, jump="", log_level=logging.ERROR):
    from .crypto import get_session, set_session

    token = secrets.token_hex(16)
    session = get_session() if jump != "top" else {}
    session |= {"token": token}
    set_session(session)

    url_map = {
        "top": (Conf["top_url"], {}),
        "kanri": (Conf["kanri_url"], {"mode": "KANRI", "token": token}),
        "": (Conf["cgi_url"], {"mode": "my_page", "token": token}),
    }

    url, par = url_map.get(jump, url_map[""])

    logging.log(log_level, f"Error: {txt}, Jump: {jump}")

    content = {
        "txt": txt,
        "url": url,
        "par": par,
        "jump": jump,  # 条件分岐用にjumpも渡す
    }

    print_html("error_tmp.html", content)


# ==========#
# リザルト #
# ==========#
def print_result(txt="", html="", token="", kanri=False):
    content = {
        "txt": txt,
        "html": html,
        "token": token,
        "kanri": kanri,
    }

    print_html("result_tmp.html", content)


# ==========#
# html出力  #
# ==========#
def print_html(tmp_name="", content={}, exit=True):
    template = env.get_template(tmp_name)
    full_content = {"Conf": Conf, **content}  # Confをデフォルトで追加

    print("Content-Type: text/html; charset=utf-8\r\n\r\n")
    print(template.render(full_content))

    if exit:
        sys.exit()


# =============#
# 数値表記変換#
# =============#
def slim_number(item):
    from .crypto import get_cookie

    def num_slice(value, unit_type):
        # カンマ区切り (1,000,000)
        if unit_type == 1:
            return f"{value:,}"

        units = {2: ["", "K", "M", "G", "T", "P"], 3: ["", "万", "億", "兆", "京"]}

        threshold = 1000 if unit_type == 2 else 10000
        if unit_type not in units:
            return str(value)

        value = float(value)
        for unit in units[unit_type]:
            if value < threshold:
                return f"{value:.2f}".rstrip("0").rstrip(".") + unit
            value /= threshold
        return str(value)

    # ユーザーのクッキーから単位タイプを取得
    cookie = get_cookie()
    unit_type = cookie.get("unit_type", 0)

    if unit_type == 0:
        return item
    if isinstance(item, (int, float)):
        return num_slice(item, unit_type)
    if isinstance(item, dict):
        return dict((k, slim_number(v)) for k, v in item.items())
    if isinstance(item, list):
        return list(map(slim_number, item))
    return item if not str(item).isdecimal() else num_slice(int(item), unit_type)
