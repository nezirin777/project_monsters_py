def zukan(FORM):
    import sub_def
    import conf

    Conf = conf.Conf

    in_name = FORM.get("name")
    m_type = FORM.get("type", "")
    fol = FORM.get("fol", "")

    zukan = sub_def.open_zukan(in_name)
    user = sub_def.open_user(in_name)
    M_list = sub_def.open_monster_dat()

    FORM["s"] = sub_def.get_session()
    ccc = sub_def.get_cookie()

    ref = ccc.get("in_name", "") == in_name

    zukan_list = {name: zu for name, zu in zukan.items() if (m_type == zu["m_type"])}

    content = {
        "Conf": Conf,
        "in_name": in_name,
        "user": user,
        "zukan_list": zukan_list,
        "m_type": m_type,
        "M_list": M_list,
        "ref": ref,
        "fol": fol,
    }

    sub_def.print_html("zukan_tmp.html", content)

    # トークン付きのユーザーページリンクまたは通常のリンク
    if ref:
        token = FORM["s"]["token"]
        sub_def.my_page_button(token)
    else:
        sub_def.footer()
