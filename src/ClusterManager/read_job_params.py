#!/usr/bin/env python

import os
import sys
import argparse
import base64
import json
import pprint

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),"../utils"))

from DataHandler import DataHandler

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--job_id", "-j", help="id of job", required=True)

    args = parser.parse_args()
    handler = DataHandler()
    jobs = handler.GetJob(jobId=args.job_id)
    if len(jobs) == 0:
        print("didn't find job of %s" % (args.job_id))
        sys.exit(1)

    job = jobs[0]
    job_params = json.loads(base64.b64decode(job["jobParams"]))

    pprint.pprint(job_params)
