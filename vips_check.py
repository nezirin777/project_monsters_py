#!D:\Python\Python314\python.exe

import sys
import io
import os
import cgi
import json
import traceback
import datetime
import time
import requests
from zoneinfo import ZoneInfo
from decimal import Decimal

from solders.pubkey import Pubkey
from sub_def.file_ops import open_vips_shop3_dat
import cgi_py.kakin_item as kakin_item
import conf

# 共通設定を読み込む
Conf = conf.Conf

# CGI の標準出力を UTF-8 にする
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
# レスポンスはテキストとして返す
print("Content-Type: text/plain; charset=utf-8\n")

# POST / GET パラメータを受け取る
form = cgi.FieldStorage()

# ログ出力用の日本時間タイムゾーン
JST = ZoneInfo("Asia/Tokyo")


def build_runtime_config(form: cgi.FieldStorage) -> dict:
    # 課金ネットワーク設定を POST 優先で決める
    posted_network = form.getfirst("network", "").strip()
    if posted_network in ("mainnet", "devnet"):
        network = posted_network
    else:
        network = Conf["network"]
        if network != "mainnet":
            network = "devnet"

    # ログ保存先ディレクトリ
    save_dir = Conf["log_dir"]

    try:
        # 利用ネットワークごとの RPC / Program / Mint を切り替える
        if network == "mainnet":
            rpc_url = Conf["rpc_mainnet"]
            token_program_id_used = Pubkey.from_string(Conf["token_program_id_mainnet"])
            item_mint = Conf["token_mint_mainnet"]
        else:
            network = "devnet"
            rpc_url = Conf["rpc_devnet"]
            token_program_id_used = Pubkey.from_string(Conf["token_program_id_devnet"])
            item_mint = Conf["token_mint_devnet"]

        # 共通のショップ受取先ウォレット
        shop_wallet = Conf["shop_wallet"]
        # 共通のトークン小数桁数
        item_decimals = int(Conf["token_decimals"])

        # ATA 導出に使う Program ID
        associated_token_program_id = Pubkey.from_string(
            Conf["associated_token_program_id"]
        )

        # 使用済みトランザクションログ
        log_file = f"{save_dir}/used_tx_{network}.jsonl"
        # エラーログ
        error_log_file = f"{save_dir}/vips_check_error_{network}.log"
        # tx 単位のロック保存先
        lock_dir = f"{save_dir}/tx_locks_{network}"

        # 商品一覧データを読み込む
        items = open_vips_shop3_dat()

        return {
            "network": network,
            "save_dir": save_dir,
            "rpc_url": rpc_url,
            "token_program_id_used": token_program_id_used,
            "item_mint": item_mint,
            "shop_wallet": shop_wallet,
            "item_decimals": item_decimals,
            "associated_token_program_id": associated_token_program_id,
            "log_file": log_file,
            "error_log_file": error_log_file,
            "lock_dir": lock_dir,
            "items": items,
        }

    except SystemExit:
        raise
    except Exception:
        append_startup_error_log(save_dir, traceback.format_exc(), network)
        print("startup error")
        print("サーバー設定の初期化に失敗しました。")
        print("管理者にお問い合わせください。")
        raise SystemExit


# 実行時設定をまとめて構築する
RUNTIME = build_runtime_config(form)

# 課金ネットワーク
network = RUNTIME["network"]
# ログ保存先ディレクトリ
SAVE_DIR = RUNTIME["save_dir"]
# 利用中の RPC URL
RPC_URL = RUNTIME["rpc_url"]
# 利用中のトークンプログラム
TOKEN_PROGRAM_ID_USED = RUNTIME["token_program_id_used"]
# 利用中のトークン Mint
ITEM_MINT = RUNTIME["item_mint"]
# ショップ受取先ウォレット
SHOP_WALLET = RUNTIME["shop_wallet"]
# トークン小数桁数
ITEM_DECIMALS = RUNTIME["item_decimals"]
# ATA 導出に使う Program ID
ASSOCIATED_TOKEN_PROGRAM_ID = RUNTIME["associated_token_program_id"]
# 使用済みトランザクションログ
LOG_FILE = RUNTIME["log_file"]
# エラーログ
ERROR_LOG_FILE = RUNTIME["error_log_file"]
# tx 単位のロック保存先
LOCK_DIR = RUNTIME["lock_dir"]
# 商品一覧データ
ITEMS = RUNTIME["items"]


def now_iso() -> str:
    # 現在時刻を日本時間の ISO 形式で返す
    return datetime.datetime.now(JST).isoformat()


def append_startup_error_log(
    save_dir: str, message: str, network_name: str = "startup"
) -> None:
    # 起動時の設定読み込み失敗を文字列ベースで追記する
    try:
        os.makedirs(save_dir, exist_ok=True)
        error_log_file = f"{save_dir}/vips_check_error_{network_name}.log"
        with open(error_log_file, "a", encoding="utf-8") as f:
            f.write(f"[{now_iso()}] {message}\n")
    except Exception:
        pass


def ensure_dirs() -> None:
    # ログ保存に必要なディレクトリを作る
    os.makedirs(SAVE_DIR, exist_ok=True)
    os.makedirs(LOCK_DIR, exist_ok=True)


def format_token_amount(amount_raw: str, decimals: int) -> str:
    # 最小単位の整数値を人間向けの小数表記へ変換する
    value = Decimal(amount_raw) / (Decimal(10) ** decimals)
    return format(value.normalize(), "f")


def parse_ui_amount_to_raw(ui_amount, decimals: int) -> str:
    # 人間向けの小数表記を最小単位の整数値へ変換する
    value = Decimal(str(ui_amount)) * (Decimal(10) ** decimals)
    return str(int(value))


def append_log(record: dict) -> None:
    # JSONL 形式で通常ログを1行追記する
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass


def append_error_log(message: str) -> None:
    # 文字列ベースのエラーログを追記する
    try:
        with open(ERROR_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{now_iso()}] {message}\n")
    except Exception:
        pass


def log_event(
    *,
    status: str,
    txid: str = "",
    item_id: str = "",
    item_name: str = "",
    user_wallet: str = "",
    user_name: str = "",
    reason: str = "",
    detail: str = "",
    amount_raw: str = "",
    amount_human: str = "",
    network: str = "",
) -> None:
    # 課金処理の状態を構造化ログとして保存する
    append_log(
        {
            "timestamp": now_iso(),
            "status": status,
            "txid": txid,
            "network": network,
            "item_id": item_id,
            "item_name": item_name,
            "user_wallet": user_wallet,
            "user_name": user_name,
            "reason": reason,
            "detail": detail,
            "amount_raw": amount_raw,
            "amount_human": amount_human,
        }
    )


def tx_used(txid: str) -> bool:
    # 同じ txid がすでに処理済みかをログから判定する
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                # 旧形式(txidだけの行)にも対応
                if line == txid:
                    return True

                try:
                    rec = json.loads(line)
                except Exception:
                    continue

                if rec.get("txid") == txid and rec.get("status") in {
                    "grant_success",
                    "grant_failed",
                    "duplicate_reject",
                }:
                    return True
    except FileNotFoundError:
        return False
    except Exception:
        return False

    return False


def lock_path_for_tx(txid: str) -> str:
    # txid ごとのロックファイルパスを作る
    safe_txid = "".join(ch for ch in txid if ch.isalnum() or ch in ("-", "_"))
    return f"{LOCK_DIR}/{safe_txid}.lock"


def acquire_tx_lock(txid: str):
    # 同一 txid の多重処理を防ぐためロックを取得する
    path = lock_path_for_tx(txid)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(now_iso())
        return path
    except FileExistsError:
        return None


def release_tx_lock(lock_path) -> None:
    # 処理終了後に tx ロックを解放する
    if not lock_path:
        return
    try:
        os.remove(lock_path)
    except FileNotFoundError:
        pass
    except Exception:
        pass


def fail_before_transfer(reason: str, user_message: str) -> None:
    # 送金確認前の失敗メッセージを返して終了する
    print(reason)
    print("送金は確認できませんでした。")
    print(user_message)
    print("アイテムは付与していません。")
    raise SystemExit


def fail_after_transfer(reason: str, user_message: str) -> None:
    # 送金確認後の失敗メッセージを返して終了する
    print(reason)
    print("送金は確認できました。")
    print(user_message)
    print("管理者にお問い合わせください。重複付与はされません。")
    raise SystemExit


def get_ata(owner: Pubkey, mint: Pubkey, program_id: Pubkey) -> Pubkey:
    # owner と mint から ATA アドレスを導出する
    seeds = [bytes(owner), bytes(program_id), bytes(mint)]
    ata, _ = Pubkey.find_program_address(seeds, ASSOCIATED_TOKEN_PROGRAM_ID)
    return ata


def rpc_call(method: str, params: list):
    # Solana RPC を HTTP JSON-RPC で1回呼び出す
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params,
    }

    r = requests.post(RPC_URL, json=payload, timeout=20)
    r.raise_for_status()

    # 空レスポンスは異常扱い
    if not r.text.strip():
        raise RuntimeError("RPC returned empty body")

    try:
        data = r.json()
    except Exception as e:
        # JSON 解析失敗時は生レスポンスもログへ残す
        append_error_log(f"rpc_call raw response: {r.text[:500]}")
        raise RuntimeError(f"Invalid JSON response: {e}")

    # JSON-RPC の error を通常例外として扱う
    if "error" in data:
        raise RuntimeError(f"RPC error: {data['error']}")
    return data["result"]


def wait_for_signature(txid: str, retries: int = 20, interval: float = 2.0):
    # 署名の確認状態を一定回数ポーリングする
    last_error = None

    for _ in range(retries):
        try:
            result = rpc_call(
                "getSignatureStatuses",
                [[txid], {"searchTransactionHistory": True}],
            )

            values = result.get("value") or []
            if values and values[0] is not None:
                st = values[0]
                err = st.get("err")
                confirmation_status = st.get("confirmationStatus")

                # チェーン上で失敗している場合
                if err is not None:
                    return {
                        "found": True,
                        "confirmed": True,
                        "err": err,
                        "last_error": last_error,
                    }

                # confirmed / finalized まで進んだら成功扱い
                if confirmation_status in ("confirmed", "finalized"):
                    return {
                        "found": True,
                        "confirmed": True,
                        "err": None,
                        "last_error": last_error,
                    }

        except Exception as e:
            # 一時的なRPC失敗も最後のエラーとして保持する
            last_error = f"{type(e).__name__}: {e}"
            append_error_log(f"wait_for_signature error: {last_error}")

        time.sleep(interval)

    return {"found": False, "confirmed": False, "err": None, "last_error": last_error}


def get_transaction_with_retry(txid: str, retries: int = 12, interval: float = 2.0):
    # confirmed 後に取引詳細が取れるまで一定回数リトライする
    for _ in range(retries):
        try:
            result = rpc_call(
                "getTransaction",
                [txid, {"encoding": "jsonParsed", "commitment": "confirmed"}],
            )
            if result is not None:
                return result
        except Exception as e:
            append_error_log(
                f"get_transaction_with_retry error: {type(e).__name__}: {e}"
            )

        time.sleep(interval)

    return None


# ログ保存用ディレクトリを初期化
ensure_dirs()

# リクエストから必要パラメータを受け取る
txid = form.getfirst("txid", "").strip()
item_id = form.getfirst("item", "").strip()
user_wallet = form.getfirst("user", "").strip()
user_name = form.getfirst("user_name", "").strip()

# 商品IDから商品定義を引く
item = ITEMS.get(item_id)

# 必須パラメータ不足なら即中止
if not txid or item is None or not user_wallet:
    log_event(
        status="request_invalid",
        txid=txid,
        item_id=item_id,
        item_name=item["name"] if item else "",
        user_wallet=user_wallet,
        user_name=user_name,
        reason="invalid request",
        network=network,
    )
    fail_before_transfer(
        "invalid request",
        "購入リクエストが不正なため、処理を中止しました。",
    )

# 同じ tx の同時処理を防ぐためロックを取る
lock_path = acquire_tx_lock(txid)

if lock_path is None:
    log_event(
        status="duplicate_reject",
        txid=txid,
        item_id=item_id,
        item_name=item["name"],
        user_wallet=user_wallet,
        user_name=user_name,
        reason="tx locked by another process",
        network=network,
    )
    print("tx locked")
    print("この取引は現在処理中です。")
    print("しばらく待ってから結果をご確認ください。")
    raise SystemExit

# 送金確認フラグ
transfer_verified = False
# 実際の送金額（最小単位）
amount_str = ""
# 表示用の送金額
amount_human = ""

try:
    # すでに処理済みの tx なら重複付与を防ぐ
    if tx_used(txid):
        log_event(
            status="duplicate_reject",
            txid=txid,
            item_id=item_id,
            item_name=item["name"],
            user_wallet=user_wallet,
            user_name=user_name,
            reason="tx already used",
            network=network,
        )
        print("tx already used")
        print("この取引はすでに処理済みです。")
        print("送金済みであっても、アイテムの重複付与は行いません。")
        raise SystemExit

    # まず署名がチェーン上で確認されるまで待つ
    sig_state = wait_for_signature(txid, retries=20, interval=2.0)

    # 署名自体が失敗している場合
    if sig_state["err"] is not None:
        log_event(
            status="verify_failed",
            txid=txid,
            item_id=item_id,
            item_name=item["name"],
            user_wallet=user_wallet,
            user_name=user_name,
            reason="signature status error",
            detail=str(sig_state["err"]),
            network=network,
        )
        fail_before_transfer(
            "signature status error",
            "送金トランザクションは失敗しています。",
        )

    # 最後まで確認できなかった場合
    if not sig_state["confirmed"]:
        log_event(
            status="verify_failed",
            txid=txid,
            item_id=item_id,
            item_name=item["name"],
            user_wallet=user_wallet,
            user_name=user_name,
            reason="signature not confirmed",
            detail=sig_state.get("last_error", ""),
            network=network,
        )
        fail_before_transfer(
            "signature not confirmed",
            "取引確認が完了しなかったため、送金確認ができませんでした。",
        )

    # 取引本体を取得して中身を検証する
    resp = get_transaction_with_retry(txid, retries=12, interval=2.0)
    if resp is None:
        log_event(
            status="verify_failed",
            txid=txid,
            item_id=item_id,
            item_name=item["name"],
            user_wallet=user_wallet,
            user_name=user_name,
            reason="tx not found after confirmation",
            network=network,
        )
        fail_before_transfer(
            "tx not found",
            "取引詳細が取得できなかったため、送金確認ができませんでした。",
        )

    # transaction 本体と message を取り出す
    encoded_tx = resp["transaction"]
    message = encoded_tx.get("message")

    # message が無ければ JSON 構造異常
    if message is None:
        log_event(
            status="verify_failed",
            txid=txid,
            item_id=item_id,
            item_name=item["name"],
            user_wallet=user_wallet,
            user_name=user_name,
            reason="transaction parse error",
            network=network,
        )
        fail_before_transfer(
            "transaction parse error",
            "取引内容を読み取れなかったため、送金確認ができませんでした。",
        )

    # 送金命令の探索用変数
    found = False
    source = None
    dest = None
    mint = None
    token_decimals = None

    # instructions から transferChecked 系の命令を探す
    for ix in message.get("instructions", []):
        parsed = ix.get("parsed")
        if not parsed:
            continue

        if parsed.get("type") in ["transferChecked", "transferCheckedWithFee"]:
            info = parsed["info"]
            mint = info.get("mint")
            source = info.get("source")
            dest = info.get("destination")
            amount_str = info["tokenAmount"].get("amount", "")
            token_decimals = info["tokenAmount"].get("decimals")
            found = True
            break

    # 対象送金が見つからなければ失敗
    if not found:
        log_event(
            status="verify_failed",
            txid=txid,
            item_id=item_id,
            item_name=item["name"],
            user_wallet=user_wallet,
            user_name=user_name,
            reason="token transfer not found",
            network=network,
        )
        fail_before_transfer(
            "token transfer not found",
            "対象となるトークン送金が確認できませんでした。",
        )

    # 実際の送金額を見やすい表示用にも変換しておく
    if amount_str and token_decimals is not None:
        amount_human = format_token_amount(amount_str, int(token_decimals))

    # 検証用のATAを導出する
    shop_pub = Pubkey.from_string(SHOP_WALLET)
    mint_pub = Pubkey.from_string(ITEM_MINT)
    user_pub = Pubkey.from_string(user_wallet)

    shop_ata = get_ata(shop_pub, mint_pub, TOKEN_PROGRAM_ID_USED)
    user_ata = get_ata(user_pub, mint_pub, TOKEN_PROGRAM_ID_USED)

    # mint 一致確認
    if mint != str(mint_pub):
        log_event(
            status="verify_failed",
            txid=txid,
            item_id=item_id,
            item_name=item["name"],
            user_wallet=user_wallet,
            user_name=user_name,
            reason="mint mismatch",
            network=network,
        )
        fail_before_transfer(
            "mint mismatch",
            "送金トークンが対象アイテムと一致しませんでした。",
        )

    # 送金元 ATA 一致確認
    if source != str(user_ata):
        log_event(
            status="verify_failed",
            txid=txid,
            item_id=item_id,
            item_name=item["name"],
            user_wallet=user_wallet,
            user_name=user_name,
            reason="source mismatch",
            network=network,
        )
        fail_before_transfer(
            "source mismatch",
            "送金元が購入者の口座と一致しませんでした。",
        )

    # 送金先 ATA 一致確認
    if dest != str(shop_ata):
        log_event(
            status="verify_failed",
            txid=txid,
            item_id=item_id,
            item_name=item["name"],
            user_wallet=user_wallet,
            user_name=user_name,
            reason="destination mismatch",
            network=network,
        )
        fail_before_transfer(
            "destination mismatch",
            "送金先がショップの受取先と一致しませんでした。",
        )

    # 商品価格を最小単位へ変換して照合する
    expected_amount = parse_ui_amount_to_raw(item["price"], ITEM_DECIMALS)
    if amount_str != expected_amount:
        log_event(
            status="verify_failed",
            txid=txid,
            item_id=item_id,
            item_name=item["name"],
            user_wallet=user_wallet,
            user_name=user_name,
            reason="amount mismatch",
            amount_raw=amount_str,
            amount_human=amount_human,
            network=network,
        )
        fail_before_transfer(
            "amount mismatch",
            "送金額が商品価格と一致しませんでした。",
        )

    # ここまで通れば送金内容の確認は完了
    transfer_verified = True

    # 成功メッセージを返す
    print("purchase success")
    print("送金は確認できました。")

    try:
        # 実際のアイテム付与処理を行う
        result = kakin_item.kakin_item(item_id, user_name)

        # 付与成功
        if result:
            log_event(
                status="grant_success",
                txid=txid,
                item_id=item_id,
                item_name=item["name"],
                user_wallet=user_wallet,
                user_name=user_name,
                amount_raw=amount_str,
                amount_human=amount_human,
                network=network,
                reason="grant success",
            )
            print("OK")
            print(f"{item['name']} を付与したよ～！")
        else:
            # 付与関数が False を返した場合
            log_event(
                status="grant_failed",
                txid=txid,
                item_id=item_id,
                item_name=item["name"],
                user_wallet=user_wallet,
                user_name=user_name,
                amount_raw=amount_str,
                amount_human=amount_human,
                network=network,
                reason="kakin_item returned False",
            )
            fail_after_transfer(
                "item grant failed",
                "送金は確認できましたが、アイテム付与に失敗しました。",
            )

    except SystemExit:
        raise
    except Exception:
        # 付与処理中の例外もログに残す
        log_event(
            status="grant_failed",
            txid=txid,
            item_id=item_id,
            item_name=item["name"],
            user_wallet=user_wallet,
            user_name=user_name,
            amount_raw=amount_str,
            amount_human=amount_human,
            network=network,
            reason="exception during item grant",
            detail=traceback.format_exc(),
        )
        append_error_log(traceback.format_exc())
        fail_after_transfer(
            "item grant exception",
            "送金は確認できましたが、付与処理中にエラーが発生しました。",
        )

except SystemExit:
    raise
except Exception as e:
    # 予期しない例外は送金確認前後でメッセージを分ける
    if transfer_verified:
        log_event(
            status="grant_failed",
            txid=txid,
            item_id=item_id,
            item_name=item["name"],
            user_wallet=user_wallet,
            user_name=user_name,
            amount_raw=amount_str,
            amount_human=amount_human,
            network=network,
            reason=type(e).__name__,
            detail=str(e),
        )
        append_error_log(traceback.format_exc())
        fail_after_transfer(
            "server error after transfer verification",
            "送金は確認できましたが、その後のサーバー処理で失敗しました。",
        )
    else:
        log_event(
            status="verify_failed",
            txid=txid,
            item_id=item_id,
            item_name=item["name"],
            user_wallet=user_wallet,
            user_name=user_name,
            amount_raw=amount_str,
            amount_human=amount_human,
            network=network,
            reason=type(e).__name__,
            detail=str(e),
        )
        append_error_log(traceback.format_exc())
        fail_before_transfer(
            "server error before transfer verification",
            "サーバー内部でエラーが発生し、送金確認が完了しませんでした。",
        )
finally:
    # 最後に必ずロックを解放する
    release_tx_lock(lock_path)
