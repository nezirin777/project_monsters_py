#!D:\Python\Python314\python.exe

import sys
import os
import requests
import conf

Conf = conf.Conf

print("Content-Type: application/json; charset=utf-8\n")

if os.environ.get("REQUEST_METHOD") != "POST":
    print('{"error":"method not allowed"}')
    sys.exit()

ref = os.environ.get("HTTP_REFERER", "")
internal_key = os.environ.get("HTTP_X_INTERNAL_RPC_KEY", "")

# Conf から読む
# 現状未使用vips_checkから呼ぶときに必要
INTERNAL_RPC_KEY = Conf["internal_rpc_key"]

# ブラウザからの通常アクセス or 内部キー付きアクセスを許可
allowed = (Conf["domain"] in ref) or (internal_key == INTERNAL_RPC_KEY)

if not allowed:
    print('{"error":"forbidden"}')
    sys.exit()

HELIUS_URL = Conf["rpc_mainnet"]

body = sys.stdin.read()

try:
    r = requests.post(
        HELIUS_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        timeout=20,
    )
    print(r.text)
except Exception as e:
    detail = str(e).replace('"', '\\"')
    print(f'{{"error":"proxy request failed","detail":"{detail}"}}')
