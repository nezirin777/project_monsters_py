import sys
import os
import secrets
import logging
import json
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

    redirect_script = (
        f"""
        <script>
            window.addEventListener('DOMContentLoaded', () => {{
                setTimeout(() => {{post("{url}", {json.dumps(par)}); }}, 1000);
            }});
        </script>
    """
        if jump in url_map
        else ""
    )

    template = env.get_template("error_tmp.html")
    html = template.render(txt=txt, redirect_script=redirect_script, ver=Conf["ver"])

    print("Content-Type: text/html; charset=utf-8\r\n\r\n")
    print(html)
    sys.exit()


# ===========#
# Javascript #
# ===========#
def jscript(party, m_name):
    scripts = []
    if party:
        p = "/" + "/".join(pt["name"] for pt in party)
        scripts.append(f'<script>main("{Conf["imgpath"]}/","{p}","{m_name}")</script>')

    return scripts


# ============#
# ログインボタン#
# ============#
def my_page_button(token=""):
    template = env.get_template("my_page_button_tmp.html")
    html = template.render(
        cgi_url=Conf["cgi_url"], top_url=Conf["top_url"], token=token, ver=Conf["ver"]
    )
    print("Content-Type: text/html; charset=utf-8\r\n\r\n")
    print(html)


# ==========#
# リザルト #
# ==========#
def result(txt="", html="", token="", kanri=False):
    template = env.get_template("result_tmp.html")
    h = template.render(
        txt=txt,
        html=html,
        cgi_url=Conf["cgi_url"],
        top_url=Conf["top_url"],
        token=token,
        ver=Conf["ver"],
        kanri=kanri,
        Conf=Conf,
    )

    print("Content-Type: text/html; charset=utf-8\r\n\r\n")
    print(h)
    sys.exit()


# ==========#
# html出力  #
# ==========#
def print_html(tmp_name="", content={}, exit=True):
    template = env.get_template(tmp_name)

    print("Content-Type: text/html; charset=utf-8\r\n\r\n")
    print(template.render(content))

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

        units = {
            2: ["", "K", "M", "G", "T", "P"],  # K/M/G
            3: ["", "万", "億", "兆", "京"],  # 万/億/兆
        }

        threshold = 1000 if unit_type == 2 else 10000
        if unit_type not in units:
            return str(value)

        value = float(value)
        for unit in units[unit_type]:
            if value < threshold:
                return f"{value:.2f}".rstrip("0").rstrip(".") + unit
            value /= threshold
        return str(value)

    def process(value, unit_type):
        if isinstance(value, (int, float)):
            return num_slice(value, unit_type)
        if isinstance(value, dict):
            return {k: process(v, unit_type) for k, v in value.items()}
        if isinstance(value, list):
            return [process(v, unit_type) for v in value]
        return value if not str(value).isdecimal() else num_slice(int(value), unit_type)

    # ユーザーのクッキーから単位タイプを取得
    cookie = get_cookie()
    unit_type = cookie.get("unit_type", 0)
    # ユニットタイプが0（変換しない）の場合はそのまま返す
    return item if unit_type == 0 else process(item, unit_type)
