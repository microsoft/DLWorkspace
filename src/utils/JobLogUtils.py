import logging
from itertools import groupby

from config import config

logger = logging.getLogger(__name__)


def TryParseCursor(cursor):
    try:
        return list(int(s) for s in cursor.split('.', 2))
    except Exception:
        logger.exception('Failed to parse cursor %s'.format(cursor))
        return None


if config.get("logging") == 'logAnalytics':
    from azure.common.credentials import ServicePrincipalCredentials
    from azure.loganalytics import LogAnalyticsDataClient

    _credentials = ServicePrincipalCredentials(
        client_id=config["activeDirectory"]["clientId"],
        secret=config["activeDirectory"]["clientSecret"],
        tenant=config["activeDirectory"]["tenant"],
        resource='https://api.loganalytics.io',
    )

    def GetJobLog(jobId, cursor=None, size=None):
        try:
            with LogAnalyticsDataClient(_credentials) as dataClient:
                query = [
                    config['logAnalytics']['tableName'] + "_CL",
                    'where kubernetes_labels_jobId_g == "{}"'.format(jobId),
                    'extend cursor=toint(_timestamp_d) + time_nsec_d / decimal(1e9)',
                    'sort by cursor asc',
                    'project cursor, kubernetes_pod_name_s, stream_s, log_s'
                ]

                if cursor is not None:
                    query.append('where cursor > decimal({})'.format(cursor))
                if size is not None:
                    query.append('limit {}'.format(size))

                query = '\n| '.join(query)
                results = dataClient.query(
                    workspace_id=config["logAnalytics"]["workspaceId"],
                    body={"query": query})

            rows = results.tables[0].rows

            pod_logs = dict()
            for pod_name, pod_rows in groupby(rows, lambda row: row[1]):
                pod_logs[pod_name] = ''.join(pod_row[3] for pod_row in pod_rows)

            if len(rows) > 0:
                cursor = rows[-1][0]
            else:
                cursor = None

            return (pod_logs, cursor)
        except Exception:
            logger.exception("Request log analytics failed")
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
        # TODO: Refer file://samba/foobar.log
        return ({}, None)
