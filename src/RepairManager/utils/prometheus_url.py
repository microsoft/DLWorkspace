#!/usr/bin/env python3

import urllib.parse
import argparse
import logging
import datetime

logger = logging.getLogger(__name__)

def format_prometheus_url_query(prometheus_url, query):
    args = urllib.parse.urlencode({"query": query})

    return urllib.parse.urljoin(prometheus_url,
            "/prometheus/api/v1/query") + "?" + args


def format_prometheus_url_query_range(prometheus_url, query, step, interval):
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
