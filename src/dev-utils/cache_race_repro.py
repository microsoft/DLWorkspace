import time
import hashlib
import argparse
import os
import sys
import random
import logging

from cachetools import cached, TTLCache
from threading import Lock, Thread

NUM_THREADS = 4
if os.getenv("NUM_THREADS"):
    NUM_THREADS = int(os.getenv("NUM_THREADS"))

NUM_RUNS = 100
if os.getenv("NUM_RUNS"):
    NUM_THREADS = int(os.getenv("NUM_RUNS"))

LOCK = None
if os.getenv("LOCK_CACHE"):
    LOCK = Lock()

KEYS = ["key%s" % str(i) for i in range(8)]


@cached(cache=TTLCache(maxsize=4, ttl=1), lock=LOCK)
def generate(key):
    return hashlib.md5((str(key) + str(time.time())).encode())


def run(worker_id):
    i = 0
    while i < NUM_RUNS:
        key = KEYS[random.randint(0, 7)]
        value = generate(key)
        logging.info("Worker %s run %s (%s, %s)" % (worker_id, i, key, value))
        time.sleep(0.1)
        i += 1


def main():
    threads = []
    for i in range(NUM_THREADS):
        t = Thread(target=run, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()


if __name__ == "__main__":
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter("[%(levelname)s %(asctime)s] %(message)s")
    handler.setFormatter(formatter)
    root.addHandler(handler)

    main()
