import logging

from itertools import groupby
from json import loads
from json.decoder import JSONDecodeError

from config import config

logger = logging.getLogger(__name__)


def TryParseCursor(cursor):
    try:
        return list(int(s) for s in cursor.split('.', 2))
    except Exception:
        logger.exception('Failed to parse cursor %s'.format(cursor))
        return None


if config.get("logging") == 'azure_blob':
    logger.info('Azure Blob log backend is enabled.')

    from azure.storage.blob import AppendBlobService
    from azure.common import AzureMissingResourceHttpError, AzureHttpError

    append_blob_service = AppendBlobService(
        connection_string=config['azure_blob_log']['connection_string'])
    container_name = config['azure_blob_log']['container_name']

    CHUNK_SIZE = 1024 * 1024  # Assume each line in log is no more then 1MB

    def GetJobLog(jobId, cursor=None, size=None):
        try:
            prefix = 'jobs.' + jobId

            lines = []

            try:
                blobs = append_blob_service.list_blobs(
                    container_name=container_name,
                    prefix=prefix)
                blobs = list(blobs)

                if len(blobs) == 0:
                    return ({}, None)

                blob = blobs[-1]
                start_range = max(0, blob.properties.content_length - CHUNK_SIZE)
                chunk = append_blob_service.get_blob_to_bytes(
                    container_name=container_name,
                    blob_name=blob.name,
                    start_range=start_range)
                content = chunk.content.decode(
                    encoding='utf-8', errors='ignore')

                content_lines = content.split('\n')
                for i, content_line in enumerate(content_lines, 1):
                    try:
                        line = loads(content_line)
                        lines.append(line)
                    except JSONDecodeError:
                        if i == 1:
                            # Normal case, invalid JSON at the start of the log:
                            #     Directly continue to next line
                            pass

                        # Bad case, invalid JSON in the middle / tail of the log:
                        #     Log it down and parse next lines
                        logger.exception(
                            'Failed to parse log line {} of job {}: {}'.format(
                                i, jobId, content_line))
            except AzureHttpError as error:
                if error.status_code in (
                        404,  # Not Found (No such job)
                        416,  # Range Not Satisfiable (No more logs)
                ):
                    return ({}, None)
                else:
                    raise

            pod_logs = dict()
            for pod_name, pod_lines in groupby(
                    lines, lambda line: line['kubernetes']['pod_name']):
                pod_lines = sorted(pod_lines, key=lambda line: line['time'])
                pod_logs[pod_name] = ''.join(
                    pod_line['log'] for pod_line in pod_lines)

            return (pod_logs, None)
        except Exception:
            logger.exception(
                "Failed to request logs of job {} from azure blob".format(
                    jobId))
            return ({}, None)
elif config.get("logging") == 'elasticsearch':
    logger.info('Elasticsearch log backend is enabled.')

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
                pod_logs[pod_name] = ''.join(pod_document["_source"]["log"]
                                             for pod_document in pod_documents)

            if len(documents) > 0:
                cursor = '.'.join(str(i) for i in documents[-1]["sort"])
            else:
                cursor = None

            return (pod_logs, cursor)
        except Exception:
            logger.exception(
                "Failed to request logs of job {} from elasticsearch".format(
                    jobId))
            return ({}, None)
else:
    logger.info('No log backend is configured')

    def GetJobLog(jobId, *args, **kwargs):
        return ({}, None)
