# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from json import dumps
from os import environ

from requests import get

from logger import logger
from microsoft_graph import iter_groups, iter_group_members

# Read environment variables
winbind_url = environ['WINBIND_URL']
restfulapi_url = environ['RESTFULAPI_URL']


def iter_group_identities():
    ''' Iterate group identities from RestfulAPI '''
    response = get(restfulapi_url + '/GetAllACL')
    response.raise_for_status()
    response_json = response.json()
    result = response_json['result']

    logger.info('Fetched {} group identities'.format(len(result)))

    yield from result


def get_identity(user_name):
    ''' Get identity info of the member '''
    params = {'userName': user_name}
    response = get(winbind_url + '/domaininfo/GetUserId', params=params)
    response.raise_for_status()
    response_json = response.json()

    logger.info('Fetched {} from winbind'.format(user_name))

    return response_json


def update_identity(user_name, identity):
    ''' Update identity info to the cluster '''
    params = {
        'userName': user_name,
        'uid': int(identity['uid']),
        'gid': int(identity['gid']),
        'groups': dumps(identity['groups'], separators=(',', ':')),
    }
    response = get(restfulapi_url + '/AddUser', params=params)
    response.raise_for_status()

    logger.info('Updated {} to cluster'.format(user_name))


failed = False


for group_identity in iter_group_identities():
    try:
        group_mail = group_identity['identityName']

        for group in iter_groups(group_mail):
            try:
                group_id = group['id']

                for member in iter_group_members(group_id):
                    try:
                        user_name = member['userPrincipalName']

                        identity = get_identity(user_name)
                        update_identity(user_name, identity)
                    except Exception:
                        failed = True
                        logger.exception('Exception in iter_group_members({})'.format(group_id))

            except Exception:
                failed = True
                logger.exception(
                    'Exception in iter_groups({})'.format(group_mail))

    except Exception:
        failed = True
        logger.exception('Exception in iter_group_identities()')


if failed:
    raise Exception('Exception raised during execution')
