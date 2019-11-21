# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from json import dumps
from logging import getLogger, FileHandler, StreamHandler
from os import environ
from sys import stdout

from dataset import connect
from oauthlib.oauth2 import BackendApplicationClient
from requests import get
from requests_oauthlib import OAuth2Session

# Read environment variables
log_level = environ.get('LOG_LEVEL', 'INFO')
log_file = environ.get('LOG_FILE')
tenant_id = environ['TENANT_ID']
client_id = environ['CLIENT_ID']
client_secret = environ['CLIENT_SECRET']
groups_id = environ['GROUPS_ID'].split(',')
winbind_url = environ['WINBIND_URL']
database_url = environ['DATABASE_URL']

# Configure logger
logger = getLogger(__name__)
logger.setLevel(log_level)
logger.addHandler(StreamHandler(stdout))
if log_file is not None:
    logger.addHandler(FileHandler(log_file))

# Initialize oauth session
client = BackendApplicationClient(client_id)
oauth = OAuth2Session(client=client)

# Fetch token
token_url_template = 'https://login.microsoftonline.com/{}/oauth2/v2.0/token'
token_url = token_url_template.format(tenant_id)
scope = ['https://graph.microsoft.com/.default']
token = oauth.fetch_token(token_url,
                          client_id=client_id,
                          client_secret=client_secret,
                          scope=scope)
logger.info('Token: {}'.format(token))

# Configure database
database = connect(database_url)
table = database['identity']


def get_members(group_id):
    ''' Get members of the group_id '''
    url_template = 'https://graph.microsoft.com/v1.0/groups/{}/members'
    url = url_template.format(group_id)
    while url is not None:
        members_response = oauth.get(url)
        members_response.raise_for_status()
        members_response_json = members_response.json()
        members = members_response_json['value']
        logger.info('Fetched {} mambers from group {}'.format(
            len(members), group_id))
        yield from members
        url = members_response_json.get('@odata.nextLink')


def get_identity(userName):
    ''' Get identity info of the member '''
    params = {'userName': userName}
    winbind_response = get(winbind_url, params=params)
    winbind_response.raise_for_status()
    winbind_response_json = winbind_response.json()
    logger.info('Fetched {} from winbind'.format(userName))
    return winbind_response_json


def sync_database(userName, identity):
    uid = int(identity['uid'])
    gid = int(identity['gid'])
    groups = dumps(identity['groups'], separators=(',', ':'))
    row = {
        'identityName': userName,
        'uid': uid,
        'gid': gid,
        'groups': groups,
    }
    table.upsert(row, keys=['identityName'])


first_exception = None

for group_id in groups_id:
    try:
        for member in get_members(group_id):
            try:
                userName = member['userPrincipalName']
                identity = get_identity(userName)
                sync_database(userName, identity)

                logger.info('Finished sync member {} with uid {}'.format(
                    userName, identity['uid']))
            except Exception as exception:
                if first_exception is None:
                    first_exception = exception
                logger.exception('Exception in member {}'.format(member))

        logger.info('Finished group {}'.format(group_id))
    except Exception as exception:
        if first_exception is None:
            first_exception = exception
        logger.exception('Exception in group {}'.format(group_id))

if first_exception is not None:
    logger.error('Raise the exception outside to mark the program as failed')
    raise first_exception
