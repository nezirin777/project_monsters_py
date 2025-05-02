def number_unit(FORM):
    import sub_def

    cookie = sub_def.get_cookie()
    cookie["unit_type"] = FORM["no"]

    sub_def.set_cookie(cookie)

    sub_def.print_result("表記方を変更しました。", "", FORM["token"])
