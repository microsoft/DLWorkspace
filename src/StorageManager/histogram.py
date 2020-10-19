import argparse
import os
import collections
import logging

from datetime import datetime

logger = logging.getLogger(__name__)


def get_tree_size_and_date(path, now, histogram):
    """Return total size of files in given path and subdirs."""
    for entry in os.scandir(path):
        if entry.is_dir(follow_symlinks=False):
            get_tree_size_and_date(entry.path, now, histogram)
        else:
            e = entry.stat(follow_symlinks=False)
            atime = datetime.fromtimestamp(e.st_atime)
            mtime = datetime.fromtimestamp(e.st_mtime)
            ctime = datetime.fromtimestamp(e.st_ctime)
            path_time = max(atime, mtime, ctime)
            days_ago = max((now - path_time).days, 0)
            size = e.st_size
            if days_ago in histogram:
                histogram[days_ago] += size
            else:
                logger.debug("%s\t%s\t%s\t%s",
                             path_time, now, days_ago, entry.path)
                histogram[float("inf")] += size


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--days", "-d",
        type=int,
        default=32,
        help="number of lookback days")
    parser.add_argument(
        "--path", "-p",
        type=str,
        default="/tmp",
        help="root path")
    parser.add_argument(
        "--debug", "-x",
        action="store_true",
        help="whether to enable debug print")
    args, _ = parser.parse_known_args()

    console_handler = logging.StreamHandler()
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO,
                        format="[%(asctime)s - %(levelname)s] %(message)s",
                        handlers=[console_handler])

    days = sorted(list(range(args.days)) + [float("inf")])
    init = [0] * (args.days + 1)
    histogram = collections.OrderedDict(zip(days, init))
    now = datetime.utcnow()

    get_tree_size_and_date(args.path, now, histogram)

    logger.info("days ago\tsize (GB)")
    total = 0
    for days_ago, size in histogram.items():
        logger.info("%s\t%s", days_ago, size / (2 ** 30))
        total += size
    logger.info("")
    logger.info("total: %s GB", total / (2 ** 30))


if __name__ == "__main__":
    main()
