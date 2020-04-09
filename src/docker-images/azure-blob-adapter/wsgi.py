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
            return Response(status=204)

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

            while True:
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
                    # Current blob is full, 4 possibilities:
                    #   P1. [->Full<-]
                    #   P2. [->Full<-, ..., Available]
                    #   P3. [->Full<-, ..., Full]
                    #   P4. [Full, ..., ->Full<-]
                    if blob_name == tag:
                        # Fist blob is full: P1, P2 or P3
                        blob_names = append_blob_service.list_blob_names(
                            container_name=container_name,
                            prefix=tag)
                        blob_names = list(blob_names)
                        if len(blob_names) == 1:
                            # P1: make it [Full, ->New<-]
                            blob_name = tag + '.1'
                            append_blob_service.create_blob(
                                container_name=container_name,
                                blob_name=blob_name)
                            continue
                        else:
                            # P2 or P3: point to the last one and retry
                            blob_name = blob_names[-1]
                            continue
                    else:
                        # P4: make it [Full, ..., Full, ->New<-]
                        suffix = int(blob_name.split('.')[-1])
                        blob_name = tag + '.' + str(suffix + 1)
                        append_blob_service.create_blob(
                            container_name=container_name,
                            blob_name=blob_name)
                        continue

                return Response(status=201)

        else:
            return Response(status=400)
    except AzureHttpError:
        logger.exception('Unhandled Azure HTTP Error')
        return Response(status=502)
    except Exception:
        logger.exception('Unhandled Exception')
        return Response(status=500)
