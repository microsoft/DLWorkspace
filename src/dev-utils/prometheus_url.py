#!/usr/bin/env python3

import urllib.parse
import argparse
import logging
import datetime

logger = logging.getLogger(__name__)


def format_prometheus_url(prometheus_url, query, since, until):
    args = urllib.parse.urlencode({
        "query": query,
        "start": str(since),
        "end": str(until),
        "step": "5m",
    })

    return urllib.parse.urljoin(prometheus_url,
                                "/prometheus/api/v1/query_range") + "?" + args


def main(args):
    print(
        format_prometheus_url(args.prometheus_url, args.query, args.since,
                              args.until))


if __name__ == "__main__":
    logging.basicConfig(
        format=
        "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)s - %(message)s",
        level=logging.INFO)

    parser = argparse.ArgumentParser(description="Generate prometheus api url for dev")
    parser.add_argument("--query", help="query to prometheus")
    parser.add_argument("--prometheus_url",
                        "-p",
                        default="http://127.0.0.1:9091",
                        help="Prometheus url, eg: http://127.0.0.1:9091")

    now = datetime.datetime.now()
    delta = datetime.timedelta(minutes=30)
    ago = int(datetime.datetime.timestamp(now - delta))
    now = int(datetime.datetime.timestamp(now))

    parser.add_argument("--since",
                        "-s",
                        type=int,
                        default=ago,
                        help="start time for generating report")
    parser.add_argument("--until",
                        "-u",
                        type=int,
                        default=now,
                        help="end time for generating report")

    args = parser.parse_args()

    main(args)
