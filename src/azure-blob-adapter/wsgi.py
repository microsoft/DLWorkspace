from azure.storage.blob import AppendBlobService
from azure.common import AzureMissingResourceHttpError
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
        message = 'X-Tag header is required.'
        logger.error(message)
        return Response(message, status=400)

    while True:
        try:
            resource_properties = append_blob_service.append_blob_from_stream(
                container_name=container_name,
                blob_name=blob_name,
                stream=request.stream,
                count=request.content_length)
            logger.info('Successfully append to blob {}/{}: {}'.format(
                container_name,
                blob_name,
                resource_properties
            ))
        except AzureMissingResourceHttpError:
            resource_properties = append_blob_service.create_blob(
                container_name=container_name,
                blob_name=blob_name)
            logger.info('Successfully create blob {}/{}: {}'.format(
                container_name,
                blob_name,
                resource_properties
            ))
        else:
            break

    return Response(status=201)
