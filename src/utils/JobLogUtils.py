import logging

from elasticsearch import Elasticsearch

from config import config

logger = logging.getLogger(__name__)


def TryParseCursor(cursor):
    try:
        return list(int(s) for s in cursor.split('.', 2))
    except Exception:
        logger.exception('Failed to parse cursor %s'.format(cursor))
        return None


def GetJobLog(jobId, cursor=None, size=None):
    try:
        elasticsearch = Elasticsearch(config['elasticsearch'])

        request_json = {
            "query": {
                "match_phrase": {
                    "kubernetes.labels.jobId": jobId
                }
            },
            "sort": [
                "@timestamp",
                {"time_nsec": {"unmapped_type": "long", "missing": 0}},
            ],
            "_source": ["kubernetes.pod_name", "stream", "log"]
        }
        if cursor is not None:
            search_after = TryParseCursor(cursor)
            if search_after is not None:
                request_json['search_after'] = search_after
        if size is not None:
            request_json['size'] = size

        response_json = elasticsearch.search(
            index="logstash-*",
            body=request_json)
        documents = response_json["hits"]["hits"]

        next_cursor = None
        if len(documents) > 0:
            next_cursor = '.'.join(str(i) for i in documents[-1]["sort"])

        return (documents, next_cursor)
    except Exception:
        logger.exception("Request elasticsearch failed")
        return ({}, None)