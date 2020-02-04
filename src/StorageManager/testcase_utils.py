import os, time
os.environ["TZ"] = "UTC"
time.tzset()


class DummyNodeStat(object):
    def __init__(self,
                 size=None,
                 atime=None,
                 mtime=None,
                 ctime=None,
                 uid=None,
                 gid=None):
        self.st_size = size if size else 0
        self.st_atime = atime if atime else 1574203167
        self.st_mtime = mtime if mtime else 1574203167
        self.st_ctime = ctime if ctime else 1574203167
        self.st_uid = uid if uid else 1000
        self.st_gid = gid if gid else 1000
