import conf

from sub_def.utils import print_html
from sub_def.file_ops import open_vips_shop3_dat

Conf = conf.Conf


def v_shop3_menu(FORM):
    token = FORM["s"]["token"]
    vips3 = open_vips_shop3_dat()

    content = {
        "Conf": Conf,
        "token": token,
        "user_name": FORM["s"].get("in_name", ""),
        "vips3": vips3,
        "SHOP_ITEMS": vips3,
        "SHOP_CONFIG": {
            "network": Conf["network"],
            "shop_wallet": Conf["shop_wallet"],
            "token_decimals": Conf["token_decimals"],
            "token_mint_mainnet": Conf["token_mint_mainnet"],
            "token_mint_devnet": Conf["token_mint_devnet"],
            "token_program_id_mainnet": Conf["token_program_id_mainnet"],
            "token_program_id_devnet": Conf["token_program_id_devnet"],
            "associated_token_program_id": Conf["associated_token_program_id"],
            "system_program_id": Conf["system_program_id"],
            "rent_sysvar": Conf["rent_sysvar"],
            "rpc_mainnet_proxy": Conf["rpc_mainnet_proxy"],
            "rpc_devnet": Conf["rpc_devnet"],
        },
    }

    print_html("vips_shop3_tmp.html", content)
