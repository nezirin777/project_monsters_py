#!D:\Python\Python314\python.exe

# progress.py - 同期処理の進捗表示

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

# ==========================================
# 常にフロントエンドが期待する形（completed, total, status）を返す
# ==========================================
try:
    if os.path.exists(progress_file):
        # json.load ではなく一度テキストとして読み込み、安全にパースする
        with open(progress_file, mode="r", encoding="utf-8") as f:
            data_str = f.read().strip()

        # 書き込み途中の一瞬で空データを拾ってしまった場合の安全対策
        if data_str:
            print(data_str)
        else:
            # 空だった場合は、とりあえず処理中として返す
            print(json.dumps({"total": 1, "completed": 0, "status": "running"}))

    else:
        # ファイルが無い＝処理完了（または開始前）とみなす
        print(json.dumps({"total": 1, "completed": 1, "status": "done"}))

except Exception as e:
    # エラーが起きてもフロントエンドを壊さないダミーデータを返す
    # ※ 本番環境ではエラー内容(e)は返さず、JSが止まらないことを優先する
    print(json.dumps({"total": 1, "completed": 0, "status": "running"}))
