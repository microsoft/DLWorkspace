from datetime import datetime
from textwrap import dedent
from unittest import TestCase
from unittest.mock import patch

from azure.storage.blob import AppendBlobService, Blob

from config import config

_CONTAINER_NAME = 'mycontainer'


@patch.dict(
    config, {
        'logging': 'azure_blob',
        'azure_blob_log': {
            'connection_string': 'UseDevelopmentStorage=true',
            'container_name': _CONTAINER_NAME,
        },
    })
class TestAzureBlob(TestCase):
    JOB_ID = 'd175'

    @staticmethod
    def create_blob(name, content=None, **kwargs):
        blob = Blob(name)
        if content is not None:
            blob.content = content
        for (key, value) in kwargs.items():
            setattr(blob.properties, key, value)
        return blob

    @patch.object(AppendBlobService, 'get_blob_to_bytes')
    @patch.object(AppendBlobService, 'list_blobs')
    def test_get_job_log(self, list_blobs, get_blob_to_bytes):
        from JobLogUtils import GetJobLog

        list_blobs.return_value = iter([
            self.create_blob('jobs.' + self.JOB_ID,
                             last_modified=datetime.min,
                             content_length=1024 * 1024 * 2),
        ])
        get_blob_to_bytes.return_value = \
            self.create_blob('jobs.' + self.JOB_ID, dedent(r'''}}}}
            {"kubernetes":{"pod_name":"master"},"time":0,"log":"content\n"}
            {{{{''').encode(encoding='utf-8'))

        logs, cursor = GetJobLog(self.JOB_ID)
        self.assertDictEqual(logs, {'master': "content\n"})
        self.assertIsNone(cursor)

        list_blobs.assert_called_once_with(container_name=_CONTAINER_NAME,
                                           prefix='jobs.' + self.JOB_ID)
        get_blob_to_bytes.assert_called_with(container_name=_CONTAINER_NAME,
                                             blob_name='jobs.' + self.JOB_ID,
                                             start_range=1024 * 1024)

    @patch.object(AppendBlobService, 'get_blob_to_bytes')
    @patch.object(AppendBlobService, 'list_blobs')
    def test_get_job_log_with_multi_blobs(self, list_blobs, get_blob_to_bytes):
        from JobLogUtils import GetJobLog

        list_blobs.return_value = iter([
            self.create_blob('jobs.' + self.JOB_ID,
                             last_modified=datetime.min,
                             content_length=1024 * 1024 * 2),
            self.create_blob('jobs.' + self.JOB_ID + '.1',
                             last_modified=datetime.min,
                             content_length=1024 * 1024 * 2),
        ])
        get_blob_to_bytes.return_value = \
            self.create_blob('jobs.' + self.JOB_ID, dedent(r'''}}}}
            {"kubernetes":{"pod_name":"master"},"time":0,"log":"content\n"}
            {{{{''').encode(encoding='utf-8'))

        logs, cursor = GetJobLog(self.JOB_ID)
        self.assertDictEqual(logs, {'master': "content\n"})
        self.assertIsNone(cursor)

        list_blobs.assert_called_once_with(container_name=_CONTAINER_NAME,
                                           prefix='jobs.' + self.JOB_ID)
        get_blob_to_bytes.assert_called_with(container_name=_CONTAINER_NAME,
                                             blob_name='jobs.' + self.JOB_ID +
                                             '.1',
                                             start_range=1024 * 1024)
