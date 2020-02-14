from elasticsearch import Elasticsearch
import logging

logger = logging.getLogger(__name__)

from config import config

def GetJobLog(jobId, size=10000):
    try:
        elasticsearch = Elasticsearch(config['elasticsearch'])
        request_json = {
            "query": {
                "match_phrase": {
                    "kubernetes.labels.jobId": jobId,
                },
            },
            # Fetch (maybe) last $size lines.
            # Lines in head microseconds might be
            # skiped if there are more than $size lines.
            "size": size,
            "sort": [
                { "@timestamp": "desc" },
            ],
            "_source": ["log", "kubernetes.pod_name", "docker.container_id", "@timestamp"],
        }

        response_json = elasticsearch.search(index="logstash-*", body=request_json)
        documents = response_json["hits"]["hits"]

        # Sore lines in microseconds asc
        return sorted((document['_source'] for document in documents),
                      key=lambda line: line['@timestamp'])
    except Exception:
        logger.exception("Request elasticsearch failed")
        return []
