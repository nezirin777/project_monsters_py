def zukan(FORM):
    import sub_def
    import conf
    from jinja2 import Environment, FileSystemLoader

    Conf = conf.Conf

    in_name = FORM.get("name")
    m_type = FORM.get("type", "")

    zukan = sub_def.open_zukan(in_name)
    user = sub_def.open_user(in_name)
    M_list = sub_def.open_monster_dat()

    FORM["s"] = sub_def.get_session()
    ccc = sub_def.get_cookie()

    ref = ccc.get("in_name", "") == in_name

    # Jinja2テンプレート環境を設定
    env = Environment(loader=FileSystemLoader("templates"), cache_size=100)
    template = env.get_template("zukan_tmp.html")

    zukan_list = {name: zu for name, zu in zukan.items() if (m_type == zu["m_type"])}
    # テンプレートに渡すデータを準備
    context = {
        "in_name": in_name,
        "user": user,
        "zukan_list": zukan_list,
        "m_type": m_type,
        "M_list": M_list,
        "Conf": Conf,
        "ref": ref,
    }

    sub_def.header()

    # テンプレートをレンダリング
    html = template.render(context)
    print(html)

    # トークン付きのユーザーページリンクまたは通常のリンク
    if ref:
        token = FORM["s"]["token"]
        sub_def.my_page_button(token)
    else:
        sub_def.footer()
