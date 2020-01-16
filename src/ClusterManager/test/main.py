#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import urllib.parse
import json
import argparse
import logging
import time

import requests

import utils

logger = logging.getLogger(__file__)

def test_regular_job_running(args):
    expected = "wantThisInLog"
    cmd = "echo %s ; sleep 1800" % (expected)

    with utils.run_job(args.rest, "regular", args.email, args.uid, args.vc, cmd) as job:
        utils.block_until_running(args.rest, job.jid)

        for _ in range(10):
            log = utils.get_job_log(args.rest, args.email, job.jid)

            if expected not in log["log"]:
                time.sleep(0.5)
        assert expected in log["log"]

def test_distributed_job_running(args):
    expected = "wantThisInLog"
    cmd = "echo %s ; sleep 1800" % (expected)

    with utils.run_job(args.rest, "distributed", args.email, args.uid, args.vc, cmd) as job:
        utils.block_until_running(args.rest, job.jid)

        for _ in range(10):
            log = utils.get_job_log(args.rest, args.email, job.jid)

            if expected not in log["log"]:
                time.sleep(0.5)
        time.sleep(100)
        assert expected in log["log"]

def main(args):
    test_regular_job_running(args)
    test_distributed_job_running(args)

if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument("--rest", "-r", required=True, help="rest api url, http://localhost:5000")
    parser.add_argument("--vc", "-v", required=True, help="vc to submit job")
    parser.add_argument("--email", "-e", required=True, help="email to submit job to rest")
    parser.add_argument("--uid", "-u", required=True, help="uid to submit job to rest")
    #parser.add_argument("--jid", "-j", required=True, help="job_id to query")
    #parser.add_argument("--k8s", "-l", required=True, help="kubernetes api uri eg. http://10.151.40.133:143")
    #parser.add_argument("--config", "-i", required=True, help="path to config dir")
    args = parser.parse_args()

    main(args)
