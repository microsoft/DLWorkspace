from azure.storage.blob import AppendBlobService
from azure.common import AzureMissingResourceHttpError, AzureHttpError
from dotenv import load_dotenv
from logging import getLogger
from os import environ
from werkzeug.wrappers import PlainRequest, Response

__all__ = ['application']

load_dotenv()
logger = getLogger(__name__)

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
        logger.exception()
        return Response(status=400)

    def append_blob():
        resource_properties = append_blob_service.append_blob_from_stream(
            container_name=container_name,
            blob_name=blob_name,
            stream=request.stream,
            count=request.content_length)
        logger.info('Successfully append to blob {} in container {}'.format(
            blob_name, container_name), extra=resource_properties)

    def create_blob():
        resource_properties = append_blob_service.create_blob(
            container_name=container_name,
            blob_name=blob_name)
        logger.info('Successfully create blob {} in container {}'.format(
            blob_name, container_name), extra=resource_properties)

    try:
        try:
            append_blob()
        except AzureMissingResourceHttpError:
            create_blob()
            append_blob()
        return Response(status=201)
    except AzureHttpError:
        logger.exception()
        return Response(status=502)
    except Exception:
        logger.exception()
        return Response(status=500)
