import os


def mkdirsAsUser(path, userId):
    pdir = os.path.dirname(path)
    if not os.path.exists(pdir):
        mkdirsAsUser(pdir, userId)
    if not os.path.exists(path):
        os.system("mkdir %s ; chown -R %s %s" % (path,userId, path))
