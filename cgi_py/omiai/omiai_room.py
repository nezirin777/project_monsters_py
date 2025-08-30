from jinja2 import Environment, FileSystemLoader
import sub_def
import conf

env = Environment(loader=FileSystemLoader("templates"), cache_size=100)
Conf = conf.Conf


def omiai_monster(omiai, target, mode, val, token, mode2="", val2=""):
    omiai_v = sub_def.slim_number_with_cookie(omiai)
    template = env.get_template("omiai_room_monster_list_tmp.html")
    return template.render(
        Conf=Conf,
        token=token,
        omiai=omiai,
        omiai_v=omiai_v,
        target=target,
        mode=mode,
        val=val,
        mode2=mode2,
        val2=val2,
    )


def omiai_room(FORM):
    in_name = FORM.get("name")
    if not in_name:
        raise ValueError("Name is required.")

    page = int(FORM.get("page", 1))
    token = FORM["token"]

    party = sub_def.open_party()
    omiai_list = sub_def.open_omiai_list()

    p2 = page * 10
    p1 = p2 - 9

    # 自分の登録モンスターを確認し、必要に応じて表示内容を変更
    txt2, txt3, txt4, txt5, txt6 = "", "", "", "", ""
    request_user, cancel, mes = "", "", ""

    if in_name in omiai_list:
        omiai = omiai_list[in_name]
        request_user = omiai.get("request")
        cancel = omiai.get("cancel")
        mes = omiai.get("mes")

        if not (omiai["baby"]):
            txt2 = omiai_monster(
                omiai, in_name, "omiai_touroku_cancel", "登録解除", token=token
            )
        else:
            txt6 = omiai_monster(
                omiai, in_name, "omiai_baby_get", "受け取る", token=token
            )
            mes = omiai["mes"]

        # 自分に来ている申請確認
        for name, v in omiai_list.items():
            if v["request"] == in_name:
                txt3 += omiai_monster(
                    v,
                    name,
                    "omiai_answer_ok",
                    "受け入れる",
                    mode2="omiai_answer_no",
                    val2="お断りする",
                    token=token,
                )

        # 自分が出している申請確認
        if omiai_list.get(request_user):
            txt4 = omiai_monster(
                omiai_list[request_user],
                request_user,
                "omiai_request_cancel",
                "申請キャンセル",
                token=token,
            )

    # 登録されている他のモンスターを表示
    for name, v in list(omiai_list.items())[p1 - 1 : p2]:
        if (
            name not in (in_name, request_user)
            and v["request"] != in_name
            and v["baby"] == ""
        ):
            txt5 += omiai_monster(v, name, "omiai_request", "申し込む", token=token)

    # ページングボタンの作成
    page_p = page - 1
    page_n = page + 1
    tex_p = []
    if page_p:
        tex_p.append({"page": page_p, "label": "前の区画"})
    if p2 + 1 <= len(omiai_list):
        tex_p.append({"page": page_n, "label": "次の区画"})

    # 登録可能モンスターの選択肢生成
    selectable_monsters = [
        {
            "index": i,
            "name": pt["name"],
            "sex": pt["sex"],
            "lv": pt["lv"],
            "hai": pt["hai"],
        }
        for i, pt in enumerate(party, 1)
        if pt["lv"] >= Conf["haigoulevel"]
    ]

    # テンプレートのレンダリング
    template = env.get_template("omiai_room_tmp.html")
    html = template.render(
        Conf=Conf,
        token=token,
        txt2=txt2,
        txt3=txt3,
        txt4=txt4,
        txt5=txt5,
        txt6=txt6,
        mes=mes,
        cancel=cancel,
        tex_p=tex_p,
        page=page,
        selectable_monsters=selectable_monsters,
    )

    sub_def.header()
    sub_def.jscript(party, "")
    print(html)
    sub_def.my_page_button(FORM["token"])
