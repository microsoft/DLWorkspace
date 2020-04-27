# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from os import environ
import logging

from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)


def build_oauth(tenant_id, client_id, client_secret):
    # Initialize oauth session
    client = BackendApplicationClient(client_id)
    oauth = OAuth2Session(client=client)

    # Fetch token
    token_url_template = 'https://login.microsoftonline.com/{}/oauth2/v2.0/token'
    token_url = token_url_template.format(tenant_id)
    scope = ['https://graph.microsoft.com/.default']
    token = oauth.fetch_token(token_url, client_id=client_id, client_secret=client_secret, scope=scope)
    logger.info('Token: {}'.format(token))
    return oauth


def _get_object(oauth, url, params=None):
    try:
        response = oauth.get(url, params=params)
        response.raise_for_status()
        response_json = response.json()

        logger.info('Fetched {} from {}'.format(response_json, url))
        return response_json
    except RequestException as exception:
        if exception.response.status_code == 404:
            logger.info('Fetched no object from {}'.format(url))
            return None
        raise


def _iter_objects(oauth, url, params=None):
    while url is not None:
        response = oauth.get(url, params=params)
        response.raise_for_status()
        response_json = response.json()
        objects = response_json['value']

        logger.info('Fetched {} objects from {}'.format(len(objects), url))

        yield from objects

        url = response_json.get('@odata.nextLink')
        params = None  # next urls contains params


def iter_groups_by_mail(oauth, group_mail, fields):
    ''' Iterate group objects '''
    url_template = "https://graph.microsoft.com/v1.0/groups?$filter=mail+eq+'{}'"
    url = url_template.format(group_mail)
    yield from _iter_objects(oauth, url, params={"$select": ','.join(fields)})


def get_user(oauth, user_mail, fields):
    ''' Get user object '''
    url_template = "https://graph.microsoft.com/v1.0/users/{}"
    url = url_template.format(user_mail)
    return _get_object(oauth, url, params={"$select": ','.join(fields)})


def iter_group_members(oauth, group_id, fields):
    ''' Iterate member objects '''
    url_template = 'https://graph.microsoft.com/v1.0/groups/{}/transitiveMembers'
    url = url_template.format(group_id)
    yield from _iter_objects(oauth, url, params={"$select": ','.join(fields)})


def iter_user_member_of(oauth, user_id, fields):
    ''' Iterate group objects of a user '''
    url_template = 'https://graph.microsoft.com/v1.0/users/{}/transitiveMemberOf'
    url = url_template.format(user_id)
    yield from _iter_objects(oauth, url, params={"$select": ','.join(fields)})


def iter_group_member_of(oauth, user_id, fields):
    ''' Iterate group objects of a group '''
    url_template = 'https://graph.microsoft.com/v1.0/groups/{}/transitiveMemberOf'
    url = url_template.format(user_id)
    yield from _iter_objects(oauth, url, params={"$select": ','.join(fields)})
