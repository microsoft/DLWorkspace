from json import loads
from azure.storage.blob import AppendBlobService

connection_string = 'DefaultEndpointsProtocol=https;AccountName=dltsdevlogs;AccountKey=/Yx5H4M3rTvIhhWtsTztR+119s4972rsAVG8u4UHiJsFc8XGWXHrlFxbwMwUu0E5/vU23c3/C+SrgeMcUEYN4w==;EndpointSuffix=core.windows.net'
append_blob_service = AppendBlobService(connection_string=connection_string)

container_name = 'azure-eastus-p40-dev1'
blob_name = 'jobs.platform.5043d3e3-c770-4533-9888-17423dce61ea'

blob = append_blob_service.get_blob_to_text(container_name, blob_name, start_range=195215)

for line in blob.content.splitlines():
    print(repr(line))
    json = loads(line)
    print(json)
