# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from os import environ

from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session

from logger import logger

# Read environment variables
tenant_id = environ['TENANT_ID']
client_id = environ['CLIENT_ID']
client_secret = environ['CLIENT_SECRET']

# Initialize oauth session
client = BackendApplicationClient(client_id)
oauth = OAuth2Session(client=client)

# Fetch token
token_url_template = 'https://login.microsoftonline.com/{}/oauth2/v2.0/token'
token_url = token_url_template.format(tenant_id)
scope = ['https://graph.microsoft.com/.default']
token = oauth.fetch_token(token_url, client_id=client_id, client_secret=client_secret, scope=scope)
logger.info('Token: {}'.format(token))


def _iter_objects(url):
    while url is not None:
        response = oauth.get(url)
        response.raise_for_status()
        response_json = response.json()
        objects = response_json['value']

        logger.info('Fetched {} objects from {}'.format(len(objects), url))

        yield from objects

        url = response_json.get('@odata.nextLink')


def iter_groups(group_mail):
    ''' Iterate group objects from Azure Active Directory '''
    url_template = "https://graph.microsoft.com/v1.0/groups?$filter=mail+eq+'{}'"
    url = url_template.format(group_mail)
    yield from _iter_objects(url)


def iter_group_members(group_id):
    ''' Iterate member objects from  '''
    url_template = 'https://graph.microsoft.com/v1.0/groups/{}/members'
    url = url_template.format(group_id)
    yield from _iter_objects(url)
