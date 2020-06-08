from datetime import datetime
from textwrap import dedent
from unittest import TestCase
from unittest.mock import call, patch

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

    @staticmethod
    def fill_blob(blob, content):
        blob = Blob(blob.name, content=content, props=blob.properties)
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

    @patch.object(AppendBlobService, 'get_blob_to_bytes')
    @patch.object(AppendBlobService, 'list_blobs')
    def test_get_job_raw_log(self, list_blobs, get_blob_to_bytes):
        from JobLogUtils import GetJobRawLog

        blobs = [
            self.create_blob('jobs.{}'.format(self.JOB_ID),
                             last_modified=datetime.min,
                             content_length=int(4e6)),
            self.create_blob('jobs.{}.2'.format(self.JOB_ID),
                             last_modified=datetime.min,
                             content_length=int(3e6)),
            self.create_blob('jobs.{}.1'.format(self.JOB_ID),
                             last_modified=datetime.min,
                             content_length=int(2e6)),
        ]
        list_blobs.return_value = iter(blobs)

        contents = [
            r'''
            {"log":''', r'''"content 1\n"}
            {"log":"content ''', r'''2\n"}
            {"log":"c''', r'''ontent 3\n"}
            ''', r'''{"log":"content 4\n"}
            {"log":"content 5''', r'''\n"}
            ''', r'''{"log":"content 6\n"}
            {"log":"content 7\n"''', r'''}
            {"log":"content 8''', r'''\n"}
            {"log":"content 9\n"}
            '''
        ]
        get_blob_to_bytes.side_effect = [
            self.fill_blob(blobs[0], contents[0].encode('utf-8')),
            self.fill_blob(blobs[0], contents[1].encode('utf-8')),
            self.fill_blob(blobs[0], contents[2].encode('utf-8')),
            self.fill_blob(blobs[0], contents[3].encode('utf-8')),
            self.fill_blob(blobs[2], contents[4].encode('utf-8')),
            self.fill_blob(blobs[2], contents[5].encode('utf-8')),
            self.fill_blob(blobs[1], contents[6].encode('utf-8')),
            self.fill_blob(blobs[1], contents[7].encode('utf-8')),
            self.fill_blob(blobs[1], contents[8].encode('utf-8')),
        ]

        logs = GetJobRawLog(self.JOB_ID)
        self.assertListEqual(list(logs), [
            'content 1\n',
            'content 2\n',
            'content 3\n',
            'content 4\n',
            'content 5\n',
            'content 6\n',
            'content 7\n',
            'content 8\n',
            'content 9\n',
        ])

        list_blobs.assert_called_once_with(_CONTAINER_NAME,
                                           'jobs.' + self.JOB_ID)
        get_blob_to_bytes.assert_has_calls([
            call(_CONTAINER_NAME,
                 'jobs.d175',
                 start_range=0,
                 end_range=1024 * 1024 * 1 - 1),
            call(_CONTAINER_NAME,
                 'jobs.d175',
                 start_range=1024 * 1024 * 1,
                 end_range=1024 * 1024 * 2 - 1),
            call(_CONTAINER_NAME,
                 'jobs.d175',
                 start_range=1024 * 1024 * 2,
                 end_range=1024 * 1024 * 3 - 1),
            call(_CONTAINER_NAME,
                 'jobs.d175',
                 start_range=1024 * 1024 * 3,
                 end_range=int(4e6) - 1),
            call(_CONTAINER_NAME,
                 'jobs.d175.1',
                 start_range=0,
                 end_range=1024 * 1024 * 1 - 1),
            call(_CONTAINER_NAME,
                 'jobs.d175.1',
                 start_range=1024 * 1024 * 1,
                 end_range=int(2e6) - 1),
            call(_CONTAINER_NAME,
                 'jobs.d175.2',
                 start_range=0,
                 end_range=1024 * 1024 * 1 - 1),
            call(_CONTAINER_NAME,
                 'jobs.d175.2',
                 start_range=1024 * 1024 * 1,
                 end_range=1024 * 1024 * 2 - 1),
            call(_CONTAINER_NAME,
                 'jobs.d175.2',
                 start_range=1024 * 1024 * 2,
                 end_range=int(3e6) - 1),
        ])
