from elasticsearch import Elasticsearch
import logging

logger = logging.getLogger(__name__)

from config import config

elasticsearch = Elasticsearch(
    config['elasticsearch'],
    sniff_on_start=True,
    sniff_on_connection_fail=True,
)

def GetJobLog(jobId, cursor=None, size=None):
    try:
        request_json = {
            "query": {
                "match_phrase": {
                    "kubernetes.labels.jobId": jobId
                }
            },
            "sort": ["@timestamp"],
            "_source": ["log", "kubernetes.pod_name", "docker.container_id"]
        }
        if cursor is not None:
            request_json['search_after'] = [cursor]
        if size is not None:
            request_json['size'] = size
        response_json = elasticsearch.search(index="logstash-*", body=request_json)
        documents = response_json["hits"]["hits"]

        next_cursor = None
        if len(documents) > 0:
            next_cursor = documents[-1]["sort"][0]

        return (documents, next_cursor)
    except Exception:
        logger.exception("Request elasticsearch failed")
        return ({}, None)