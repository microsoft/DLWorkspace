DATETIME_FMT = "%Y/%m/%d %H:%M:%S"
K = 2 ** 10
M = 2 ** 20
G = 2 ** 30

DAY = 86400


def bytes2human_readable(value):
    if value // G > 0:
        return "%dG" % (value // G)
    if value // M > 0:
        return "%dM" % (value // M)
    if value // K > 0:
        return "%dK" % (value // K)
    return "%d" % value
