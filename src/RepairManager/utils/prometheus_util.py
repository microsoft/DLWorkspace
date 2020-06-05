#!/usr/bin/env python3

import urllib.parse
import argparse
import logging
import datetime

logger = logging.getLogger(__name__)


def format_url_query(prometheus_url, query):
    args = urllib.parse.urlencode({"query": query})

    return urllib.parse.urljoin(prometheus_url,
                                "/prometheus/api/v1/query") + "?" + args


def format_url_query_range(prometheus_url, query, step, interval):
    now = datetime.datetime.now()
    delta = datetime.timedelta(minutes=interval)
    since = int(datetime.datetime.timestamp(now - delta))
    until = int(datetime.datetime.timestamp(now))

    args = urllib.parse.urlencode({
        "query": query,
        "start": str(since),
        "end": str(until),
        "step": str(step),
    })

    return urllib.parse.urljoin(prometheus_url,
                                "/prometheus/api/v1/query_range") + "?" + args


def extract_ips_from_response(response):
    r_json = response.json()
    node_ips = []
    if 'data' in r_json:
        metrics = r_json['data']['result']
        if metrics:
            node_ips = []
            for m in metrics:
                instance = m['metric']['instance'].split(':')[0]
                node_ips.append(instance)
    return node_ips
