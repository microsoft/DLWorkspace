# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from json import dumps
from os import environ

from requests import get

from logger import logger

# Read environment variables
restfulapi_url = environ['RESTFULAPI_URL']


def iter_acls():
    ''' Iterate group identities from RestfulAPI '''
    response = get(restfulapi_url + '/GetAllACL')
    response.raise_for_status()
    response_json = response.json()
    result = response_json['result']

    logger.info('Fetched {} ACLs'.format(len(result)))

    yield from result


def update_identity(user_name, uid, gid, groups):
    ''' Update identity info to the cluster '''
    params = {
        'userName': user_name,
        'uid': int(uid),
        'gid': int(gid),
        'groups': dumps(groups, separators=(',', ':')),
    }
    response = get(restfulapi_url + '/AddUser', params=params)
    response.raise_for_status()

    logger.info('Updated {} to cluster'.format(user_name))
