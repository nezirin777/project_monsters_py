# 排他ロッククラス
#
# exLock.py Version 1.01 written by fuku@rouge.gr.jp

"""使い方
import exLock

lock = exLock.exLock("./lockPath.LCK")
lock.lock()
lock.unlock()
"""

import os
import time


class exLock:
    def __init__(
        self,
        lockDir,
        stale_seconds=60,
        retry_count=30,
        retry_interval=1.0,
    ):
        self.lockDir = lockDir
        self.result = False
        self.stale_seconds = stale_seconds
        self.retry_count = retry_count
        self.retry_interval = retry_interval

    def lock(self):
        # 古いロックを掃除
        try:
            if os.path.isdir(self.lockDir):
                mtime = os.path.getmtime(self.lockDir)
                if time.time() - mtime > self.stale_seconds:
                    try:
                        os.rmdir(self.lockDir)
                    except OSError:
                        pass
        except Exception:
            pass

        self.result = False

        for _ in range(self.retry_count):
            try:
                os.mkdir(self.lockDir)
                self.result = True
                return True
            except FileExistsError:
                time.sleep(self.retry_interval)
            except Exception:
                time.sleep(self.retry_interval)

        return False

    def unlock(self):
        if not self.result:
            return

        try:
            if os.path.isdir(self.lockDir):
                os.rmdir(self.lockDir)
        except Exception:
            pass
        finally:
            self.result = False
