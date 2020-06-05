from os import environ
from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

# https://docs.microsoft.com/en-us/azure/storage/common/storage-use-emulator
environ['AZURE_STORAGE_CONNECTION_STRING'] = 'UseDevelopmentStorage=true'
environ['AZURE_STORAGE_CONTAINER_NAME'] = 'mycontainer'

from wsgi import application  # noqa: E402


def test_healthz(requests_mock):
    requests_mock.get('/devstoreaccount1/mycontainer?restype=container')
    client = Client(application, BaseResponse)
    response = client.get('/healthz')
    assert response.status_code == 204


def test_append_first_not_exists(requests_mock):
    requests_mock.put('/devstoreaccount1/mycontainer/jobs.d175?comp=appendblock',
                      complete_qs=True,
                      response_list=[
                          dict(status_code=404),
                          dict(status_code=201, headers={'last-modified': 'Wed, 01 Jan 2020 00:00:00 GMT'}),
                      ])
    requests_mock.put('/devstoreaccount1/mycontainer/jobs.d175',
                      complete_qs=True,
                      status_code=201,
                      headers={'last-modified': 'Wed, 01 Jan 2020 00:00:00 GMT'})

    client = Client(application, BaseResponse)
    response = client.post('/', headers={'x-tag': 'jobs.d175'}, data="log content")
    assert response.status_code == 201
    assert requests_mock.call_count == 3


def test_append_first(requests_mock):
    requests_mock.put('/devstoreaccount1/mycontainer/jobs.d175?comp=appendblock',
                      status_code=201,
                      headers={'last-modified': 'Wed, 01 Jan 2020 00:00:00 GMT'})
    client = Client(application, BaseResponse)
    response = client.post('/', headers={'x-tag': 'jobs.d175'}, data="log content")
    assert response.status_code == 201


def test_append_first_full(requests_mock):
    requests_mock.put('/devstoreaccount1/mycontainer/jobs.d175?comp=appendblock', complete_qs=True,
                      status_code=409)  # 1
    requests_mock.get('/devstoreaccount1/mycontainer?restype=container&comp=list&prefix=jobs.d175',
                      complete_qs=True,
                      headers={'Content-Type': 'application/xml'},
                      text="""<?xml version="1.0" encoding="utf-8"?>
<EnumerationResults>
    <Blobs>
        <Blob>
            <Name>jobs.d175</Name>
            <Properties>
                <Last-Modified>Wed, 01 Jan 2020 00:00:00 GMT</Last-Modified>
            </Properties>
        </Blob>
    </Blobs>
</EnumerationResults>
""")  # 2
    requests_mock.put('/devstoreaccount1/mycontainer/jobs.d175.1',
                      complete_qs=True,
                      status_code=201,
                      headers={'last-modified': 'Wed, 01 Jan 2020 00:00:00 GMT'})  # 3
    requests_mock.put(
        '/devstoreaccount1/mycontainer/jobs.d175.1?comp=appendblock',
        complete_qs=True,
        response_list=[
            dict(status_code=201, headers={'last-modified': 'Wed, 01 Jan 2020 00:00:00 GMT'})  # 4
        ])

    client = Client(application, BaseResponse)
    response = client.post('/', headers={'x-tag': 'jobs.d175'}, data="log content")
    assert response.status_code == 201
    assert requests_mock.call_count == 4


def test_append_second(requests_mock):
    requests_mock.put('/devstoreaccount1/mycontainer/jobs.d175?comp=appendblock', complete_qs=True,
                      status_code=409)  # 1
    requests_mock.get('/devstoreaccount1/mycontainer?restype=container&comp=list&prefix=jobs.d175',
                      complete_qs=True,
                      headers={'Content-Type': 'application/xml'},
                      text="""<?xml version="1.0" encoding="utf-8"?>
<EnumerationResults>
    <Blobs>
        <Blob>
            <Name>jobs.d175</Name>
            <Properties>
                <Last-Modified>Wed, 01 Jan 2020 00:00:00 GMT</Last-Modified>
            </Properties>
        </Blob>
        <Blob>
            <Name>jobs.d175.1</Name>
            <Properties>
                <Last-Modified>Wed, 01 Jan 2020 00:00:01 GMT</Last-Modified>
            </Properties>
        </Blob>
    </Blobs>
</EnumerationResults>
""")  # 2
    requests_mock.put(
        '/devstoreaccount1/mycontainer/jobs.d175.1?comp=appendblock',
        complete_qs=True,
        response_list=[
            dict(status_code=201, headers={'last-modified': 'Wed, 01 Jan 2020 00:00:00 GMT'})  # 3
        ])

    client = Client(application, BaseResponse)
    response = client.post('/', headers={'x-tag': 'jobs.d175'}, data="log content")
    assert response.status_code == 201
    assert requests_mock.call_count == 3


def test_append_second_full(requests_mock):
    requests_mock.put('/devstoreaccount1/mycontainer/jobs.d175?comp=appendblock', complete_qs=True,
                      status_code=409)  # 1
    requests_mock.get('/devstoreaccount1/mycontainer?restype=container&comp=list&prefix=jobs.d175',
                      complete_qs=True,
                      headers={'Content-Type': 'application/xml'},
                      text="""<?xml version="1.0" encoding="utf-8"?>
<EnumerationResults>
    <Blobs>
        <Blob>
            <Name>jobs.d175</Name>
            <Properties>
                <Last-Modified>Wed, 01 Jan 2020 00:00:00 GMT</Last-Modified>
            </Properties>
        </Blob>
        <Blob>
            <Name>jobs.d175.1</Name>
            <Properties>
                <Last-Modified>Wed, 01 Jan 2020 00:00:01 GMT</Last-Modified>
            </Properties>
        </Blob>
    </Blobs>
</EnumerationResults>
""")  # 2
    requests_mock.put('/devstoreaccount1/mycontainer/jobs.d175.1?comp=appendblock', complete_qs=True,
                      status_code=409)  # 3
    requests_mock.put(
        '/devstoreaccount1/mycontainer/jobs.d175.2',
        complete_qs=True,
        response_list=[
            dict(
                status_code=201,  # 4
                headers={'last-modified': 'Wed, 01 Jan 2020 00:00:00 GMT'})
        ])
    requests_mock.put(
        '/devstoreaccount1/mycontainer/jobs.d175.2?comp=appendblock',
        complete_qs=True,
        response_list=[
            dict(
                status_code=201,  # 5
                headers={'last-modified': 'Wed, 01 Jan 2020 00:00:00 GMT'})
        ])

    client = Client(application, BaseResponse)
    response = client.post('/', headers={'x-tag': 'jobs.d175'}, data="log content")
    assert response.status_code == 201
    assert requests_mock.call_count == 5
