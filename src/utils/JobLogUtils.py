import requests
import logging

logger = logging.getLogger(__name__)

from config import config

def GetJobLog(jobId, cursor=None, size=None):
    try:
        request_json = {
            "query": {
                "match_phrase": {
                    "kubernetes.labels.jobId": jobId
                }
            },
            "sort": ["@timestamp"],
            "_source": ["log", "kubernetes.pod_name"]
        }
        if cursor is not None:
            request_json['search_after'] = [cursor]
        if size is not None:
            request_json['size'] = size
        response = requests.get(config['elasticsearch'] + '/logstash-*/_search', json=request_json)
        response_json = response.json()
        documents = response_json["hits"]["hits"]

        pod_logs = {}
        for document in documents:
            try:
                pod_name = document["_source"]["kubernetes"]["pod_name"]
                log = document["_source"]["log"]
                if pod_name in pod_logs:
                    pod_logs[pod_name] += log
                else:
                    pod_logs[pod_name] = log
            except Exception:
                logging.exception("Failed to parse elasticsearch document: {}".format(document))

        next_cursor = None
        if len(documents) > 0:
            next_cursor = documents[-1]["sort"][0]

        return (pod_logs, next_cursor)
    except Exception:
        logger.exception("Request elasticsearch failed")
        return ({}, None)