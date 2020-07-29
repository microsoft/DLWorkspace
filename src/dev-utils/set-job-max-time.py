#!/usr/bin/env python3

import urllib.parse
import argparse
import sys

import requests


def get_jobs(rest, user, vc, count):
    args = urllib.parse.urlencode({
        "userName": user,
        "vcName": vc,
        "jobOwner": "all",
        "num": str(count),
    })

    url = urllib.parse.urljoin(rest, "/ListJobsV2") + "?" + args

    return requests.get(url).json()


def set_job_max_time(rest, user, jid, second):
    args = urllib.parse.urlencode({
        "userName": user,
        "jobId": jid,
        "second": str(second),
    })

    url = urllib.parse.urljoin(rest, "/JobMaxTime") + "?" + args

    resp = requests.post(url)
    resp.raise_for_status()


def main(args):
    if args.action not in ["list", "change"]:
        print("unknown action")
        sys.exit(1)

    resp = get_jobs(args.rest, args.user, args.vc, args.count)

    all_count = 0
    for key in [
            "queuedJobs", "runningJobs", "finishedJobs", "visualizationJobs"
    ]:
        all_count += len(resp[key])

    needs_fix = set()

    for key in ["queuedJobs", "runningJobs"]:
        for queued in resp[key]:
            if queued["jobParams"].get("maxTimeSec") is None:
                needs_fix.add(queued["jobParams"]["jobId"])

    print("fetched %d need to fix %s" % (all_count, len(needs_fix)))

    if args.action == "list":
        for jid in needs_fix:
            print(jid)
    elif args.action == "change":
        seconds = args.max * 24 * 3600

        count = 0
        finished = 0

        for jid in needs_fix:
            set_job_max_time(args.rest, args.user, jid, seconds)
            count += 1
            if count > 10:
                finished += count
                count = 0
                print("finished %d" % (finished))

        finished += count
        count = 0
        print("finished %d" % (finished))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["list", "change"])
    parser.add_argument("--rest", "-r", required=True, help="url to restfulapi")
    parser.add_argument("--user", "-u", required=True, help="user email")
    parser.add_argument("--vc", "-v", required=True, help="vc name")
    parser.add_argument("--count",
                        "-c",
                        default=5000,
                        type=int,
                        help="count of job to query")
    parser.add_argument("--max",
                        "-m",
                        type=int,
                        required=True,
                        help="max time to set, in unit of day")
    args = parser.parse_args()
    main(args)
