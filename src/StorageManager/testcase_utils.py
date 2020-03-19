import os
import time
import platform

SYSTEM = platform.system()
WINDOWS = "Windows"
LINUX = "Linux"

if SYSTEM is LINUX:
    os.environ["TZ"] = "UTC"
    time.tzset()

EMPTY_DIR_SIZE = 4096 if SYSTEM is LINUX else 0


class DummyNodeStat(object):
    def __init__(self,
                 ino=1,
                 nlink=1,
                 size=0,
                 atime=1574203167,
                 mtime=1574203167,
                 ctime=1574203167,
                 uid=1000,
                 gid=1000):
        self.st_ino = ino
        self.st_nlink = nlink
        self.st_size = size
        self.st_atime = atime
        self.st_mtime = mtime
        self.st_ctime = ctime
        self.st_uid = uid
        self.st_gid = gid
