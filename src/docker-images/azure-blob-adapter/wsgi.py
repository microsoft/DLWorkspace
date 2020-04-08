from azure.storage.blob import AppendBlobService
from azure.common import AzureMissingResourceHttpError, AzureConflictHttpError, AzureHttpError
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

connection_string = environ['AZURE_STORAGE_CONNECTION_STRING']
container_name = environ['AZURE_STORAGE_CONTAINER_NAME']

append_blob_service = AppendBlobService(connection_string=connection_string)


@PlainRequest.application
def application(request):
    '''
    :param PlainRequest request:
    '''
    try:
        if request.method == 'GET' and request.path == '/healthz':
            append_blob_service.get_container_properties(
                container_name=container_name)
            return Response(status=200)

        elif request.method == 'POST' and request.path == '/':
            try:
                tag = request.headers['X-Tag']
            except KeyError:
                logger.exception('Key Error')
                return Response(status=400)

            blob = request.get_data()
            count = request.content_length

            suffix = 0
            blob_name = tag

            for _ in range(10):
                try:
                    append_blob_service.append_blob_from_bytes(
                        container_name=container_name,
                        blob_name=blob_name,
                        blob=blob,
                        count=count)
                except AzureMissingResourceHttpError:
                    append_blob_service.create_blob(
                        container_name=container_name,
                        blob_name=blob_name)
                    continue
                except AzureConflictHttpError:
                    suffix += 1
                    blob_name = tag + '.' + str(suffix)
                    continue
                except AzureHttpError:
                    logger.exception('Azure HTTP Error')
                    return Response(status=502)

                return Response(status=201)

        else:
            return Response(status=400)
    except Exception:
        logger.exception('Exception')
        return Response(status=500)
