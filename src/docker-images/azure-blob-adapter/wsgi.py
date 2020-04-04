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
        if request.method == 'GET' and request.path == '/healthz':
            container = append_blob_service.get_container_properties(
                container_name=container_name)
            return Response(status=200)

        if request.method == 'POST' and request.path == '/':
            try:
                blob_name = request.headers['X-Tag']
            except KeyError:
                logger.exception('Key Error')
                return Response(status=400)

            try:
                blob = request.get_data()
                count = request.content_length
                try:
                    resource_properties = append_blob_service.append_blob_from_bytes(
                        container_name=container_name,
                        blob_name=blob_name,
                        blob=blob,
                        count=count)
                except AzureMissingResourceHttpError:
                    resource_properties = append_blob_service.create_blob(
                        container_name=container_name,
                        blob_name=blob_name)
                    resource_properties = append_blob_service.append_blob_from_bytes(
                        container_name=container_name,
                        blob_name=blob_name,
                        blob=blob,
                        count=count)
                return Response(status=201)
            except AzureHttpError:
                logger.exception('Azure HTTP Error')
                return Response(status=502)

        return Response(status=400)
    except Exception:
        logger.exception('Exception')
        return Response(status=500)
