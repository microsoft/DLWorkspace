#!/usr/bin/python

import urllib.parse
import argparse
import requests
import logging
import faulthandler
import signal
import json

import flask
from flask import Flask
from flask import request

logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.route("/kill", methods=["POST"])
def kill():
    args = request.args
    auth = request.headers.get("Authorization")
    if auth != "Bearer shinigami":
        logger.warning("get unauthorized call")
        return "Unauthorized", 401
    try:
        body = json.loads(request.data.decode("utf-8"))

        for alert in body["alerts"]:
            if alert.get("status") == "resolved":
                continue
            logger.info("processing alert of %s", alert)
            if not dry_run:
                job_name = alert["labels"]["job_name"]
                idle_hour_desc = alert.get("annotations",
                                           {}).get("idle_hour", "too long")
                params = {
                    "jobId":
                        job_name,
                    "userName":
                        "Administrator",
                    "desc":
                        "killed because the job is being idle for %s" %
                        (idle_hour_desc)
                }
                args = urllib.parse.urlencode(params)
                url = restful_url + "/KillJob?" + args

                response = requests.get(url, timeout=10)
                response.raise_for_status()
                result = response.json().get("result")
                if result is not None and result.startswith("Success"):
                    logger.info("killing %s success", params)
                else:
                    logger.warning("killing %s failed", params)
            else:
                logger.info("reaper in dry_run mode, will not kill %s", alert)
        return "Ok", 200
    except Exception as e:
        logger.exception("caught exception while processing kill, data is %s",
                         request.data)
        raise e


def register_stack_trace_dump():
    faulthandler.register(signal.SIGTRAP, all_threads=True, chain=False)


def main(args):
    app.run(host="0.0.0.0", port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    register_stack_trace_dump()
    logging.basicConfig(
        format=
        "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)s@%(thread)d - %(message)s",
        level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument("--port",
                        "-p",
                        default=9500,
                        type=int,
                        help="port to listen, default 9500")
    parser.add_argument("--restful_url",
                        "-r",
                        required=True,
                        help="restful api url, e.g. http://localhost:5000")
    parser.add_argument("--dry_run",
                        "-d",
                        action="store_true",
                        help="if dry_run, the reaper will do nothing")
    args = parser.parse_args()

    global dry_run
    global restful_url

    dry_run = args.dry_run
    restful_url = args.restful_url

    main(args)
