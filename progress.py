#!D:\Python\Python312\python.exe

import json
import os
import conf

# 設定ファイルからデータディレクトリを取得
Conf = conf.Conf
datadir = Conf["savedir"]

# 進捗情報を保存しているファイル
progress_file = os.path.join(datadir, "progress.json")

# CGIレスポンスのヘッダー
print("Content-Type: application/json\n")

progress = {"completed": 0, "total": 1}  # 初期値  # 初期値（0除算を防ぐ）

try:
    # 進捗情報を読み取る
    if os.path.exists(progress_file):
        with open(progress_file, mode="r", encoding="utf-8") as f:
            progress = json.load(f)
            print(json.dumps(progress))  # 進捗情報をJSON形式で出力
    else:
        print(json.dumps({"error": "進捗情報が見つかりません"}))
except Exception as e:
    print(json.dumps({"error": f"進捗情報の読み取り中にエラーが発生しました: {e}"}))
