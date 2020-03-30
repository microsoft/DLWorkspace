import logging

from itertools import groupby
from json import loads

from config import config

logger = logging.getLogger(__name__)


def TryParseCursor(cursor):
    try:
        return list(int(s) for s in cursor.split('.', 2))
    except Exception:
        logger.exception('Failed to parse cursor %s'.format(cursor))
        return None


def TryParseJSON(string):
    try:
        return loads(string)
    except Exception:
        logger.exception('Failed to parse json {}'.format(string))
        return None


if config.get("logging") == 'azureBlob':
    from azure.storage.blob import AppendBlobService
    from azure.common import AzureHttpError

    append_blob_service = AppendBlobService(
        connection_string=config['azureBlobLog']['connectionString'])
    container_name = config['azureBlobLog']['containerName']

    def GetJobLog(jobId, cursor=None, size=None):
        try:
            blob_name = 'jobs.' + jobId
            start_range = None
            if cursor is not None:
                try:
                    start_range = int(cursor)
                except Exception:
                    logger.exception('Failed to parse cursor')

            try:
                blob = append_blob_service.get_blob_to_text(
                    container_name=container_name,
                    blob_name=blob_name,
                    start_range=start_range
                )
                lines = blob.content.splitlines()
                lines = (TryParseJSON(line) for line in lines)
                lines = (line for line in lines if line is not None)
                lines = list(lines)
            except AzureHttpError as error:
                if error.status_code == 404 or error.status_code == 416:
                    return ({}, None)
                else:
                    raise

            pod_logs = dict()
            for pod_name, pod_lines in groupby(lines, lambda line: line['kubernetes']['pod_name']):
                pod_logs[pod_name] = ''.join(pod_line['log'] for pod_line in pod_lines)

            cursor = (start_range or 0) + blob.properties.content_length

            return (pod_logs, cursor)
        except Exception:
            logger.exception("Request azure blob failed")
            return ({}, None)
elif config.get("logging") == 'elasticsearch':
    from elasticsearch import Elasticsearch

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
                    {
                        "time_nsec": {
                            "unmapped_type": "long",
                            "missing": 0
                        }
                    },
                ],
                "_source": [
                    "docker.container_id", "kubernetes.pod_name", "stream",
                    "log"
                ]
            }
            if cursor is not None:
                search_after = TryParseCursor(cursor)
                if search_after is not None:
                    request_json['search_after'] = search_after
            if size is not None:
                request_json['size'] = size

            response_json = elasticsearch.search(index="logstash-*",
                                                 body=request_json)
            documents = response_json["hits"]["hits"]

            pod_logs = dict()
            for pod_name, pod_documents in groupby(
                    documents, lambda document: document["_source"][
                        "kubernetes"]["pod_name"]):
                pod_logs[pod_name] = ''.join(
                    pod_document["_source"]["log"] for pod_document in pod_documents)

            if len(documents) > 0:
                cursor = '.'.join(str(i) for i in documents[-1]["sort"])
            else:
                cursor = None

            return (pod_logs, cursor)
        except Exception:
            logger.exception("Request elasticsearch failed")
            return ({}, None)
else:
    def GetJobLog(jobId, *args, **kwargs):
        return ({}, None)