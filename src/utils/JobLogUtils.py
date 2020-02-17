from elasticsearch import Elasticsearch
from elasticsearch.helpers import scan
import logging

logger = logging.getLogger(__name__)

from config import config

def GetJobLog(jobId):
    try:
        elasticsearch = Elasticsearch(config['elasticsearch'])
        request_json = {
            "query": {
                "match_phrase": {
                    "kubernetes.labels.jobId": jobId,
                },
            },
            "_source": ["log", "kubernetes.pod_name", "docker.container_id", "@timestamp"],
        }
        documents = scan(elasticsearch, request_json)

        # Sore lines in microseconds asc
        return sorted((document['_source'] for document in documents),
                      key=lambda line: line['@timestamp'])
    except Exception:
        logger.exception("Request elasticsearch failed")
        return []
