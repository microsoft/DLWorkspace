from azure.storage.blob import AppendBlobService
from azure.common import AzureMissingResourceHttpError, AzureHttpError
from dotenv import load_dotenv
from logging import getLogger, StreamHandler
from os import environ
from sys import stdout
from werkzeug.wrappers import PlainRequest, Response

__all__ = ['application']

load_dotenv()

logger = getLogger(__name__)
logger.setLevel('INFO')
logger.addHandler(StreamHandler(stdout))

append_blob_service = AppendBlobService(connection_string=environ['AZURE_STORAGE_CONNECTION_STRING'])
container_name = environ['AZURE_STORAGE_CONTAINER_NAME']


@PlainRequest.application
def application(request):
    '''
    :param PlainRequest request:
    '''
    try:
        blob_name = request.headers['X-Tag']
    except KeyError:
        logger.exception('Key Error')
        return Response(status=400)

    def append_blob():
        resource_properties = append_blob_service.append_blob_from_stream(
            container_name=container_name,
            blob_name=blob_name,
            stream=request.stream,
            count=request.content_length)
        logger.info('Successfully append {} bytes to blob {} in container {}: {}'.format(
            request.content_length, blob_name, container_name, resource_properties.etag))

    def create_blob():
        resource_properties = append_blob_service.create_blob(
            container_name=container_name,
            blob_name=blob_name)
        logger.info('Successfully create blob {} in container {}: {}'.format(
            blob_name, container_name, resource_properties.etag))

    try:
        try:
            append_blob()
        except AzureMissingResourceHttpError:
            create_blob()
            append_blob()
        return Response(status=201)
    except AzureHttpError:
        logger.exception('Azure HTTP Error')
        return Response(status=502)
    except Exception:
        logger.exception('Exception')
        return Response(status=500)
