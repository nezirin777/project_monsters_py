# 排他ロッククラス
#
# exLock.py Version 1.01 written by fuku@rouge.gr.jp

"""使い方
import exLock

lock = exLock.exLock("./lockPath.LCK")
lock.lock()
lock.unlock()
"""

import os, time, stat
from sub_def.utils import error


class exLock:

    def __init__(self, lockDir):
        self.lockDir = lockDir
        self.result = False

    def lock(self):
        # 20秒以上前に作成されたロックファイルを削除する
        # ※何らかの原因で残ったままになったロックファイル
        #
        try:
            fileStat = os.stat(self.lockDir)
            timeStamp = fileStat[stat.ST_MTIME]
            if timeStamp < (time.time() - 20):
                os.rmdir(self.lockDir)
        except:
            pass

        # ロックファイルを作成してみる
        # ※5回やってダメなら失敗とする
        self.result = False
        for i in range(5):
            try:
                os.mkdir(self.lockDir)
                self.result = True  # ロックを自分で作ったという印
                break
            except OSError:
                time.sleep(1)
        if self.result == False:
            error("現在サーバーが込み合っています。", "top")
        return self.result

    def unlock(self):
        if self.result == True:  # 自分で作ったロックファイルなら消す
            os.rmdir(self.lockDir)
        self.result = False

    def __del__(self):
        if self.result == True:  # 自分で作ったロックファイルなら消す
            os.rmdir(self.lockDir)
        self.result = False
