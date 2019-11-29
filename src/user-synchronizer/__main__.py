# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from json import dumps
from os import environ

from requests import get
from yaml import safe_load

from logger import logger
from microsoft_graph import iter_groups, iter_group_members, iter_user_member_of

# Read environment variables
restfulapi_url = environ['RESTFULAPI_URL']
domain_offset_file = environ.get('DOMAIN_OFFSET_FILE', None)

# Initialize domain offset map
domain_offset = {}
try:
    with open(domain_offset_file, 'r') as domain_offset_file_stream:
    domain_offset = safe_load(domain_offset_file_stream)
except Exception:
    logger.exception('Failed to read domain offset file')
defult_domain_offset = domain_offset.get('*', 0)


def add_domain_offset(domain_name, security_identifier):
    rid = int(security_identifier.split('-')[-1])
    return domain_offset.get(domain_name, defult_domain_offset) + rid


def iter_group_identities():
    ''' Iterate group identities from RestfulAPI '''
    response = get(restfulapi_url + '/GetAllACL')
    response.raise_for_status()
    response_json = response.json()
    result = response_json['result']

    logger.info('Fetched {} group identities'.format(len(result)))

    yield from result


def get_identity(user_id, on_premises_domain_name, on_premises_security_identifier):
    ''' Get identity info of the member '''
    uid = add_domain_offset(on_premises_domain_name, on_premises_security_identifier)
    gid = add_domain_offset(on_premises_domain_name, '513')

    groups = []
    for group in iter_user_member_of(user_id, [
        'id',
        'displayName',
        'onPremisesDomainName',
        'onPremisesSecurityIdentifier',
    ]):
        try:
            if group['onPremisesDomainName'] is None:
                continue
            if group['onPremisesSecurityIdentifier'] is None:
                continue
            groups.append(str(add_domain_offset(
                group['onPremisesDomainName'],
                group['onPremisesSecurityIdentifier']
            )))
        except Exception:
            logger.exception('Exception in processing group', group)

    return {
        'uid': uid,
        'gid': gid,
        'groups': groups,
    }


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


for group_identity in iter_group_identities():
    try:
        group_mail = group_identity['identityName']

        for group in iter_groups(group_mail, ['id', 'displayName']):
            try:
                group_id = group['id']

                for member in iter_group_members(group_id, [
                    'id',
                    'displayName',
                    'userPrincipalName',
                    'onPremisesDomainName',
                    'onPremisesSecurityIdentifier',
                ]):
                    try:
                        user_id = member['id']
                        user_name = member['userPrincipalName']

                        identity = get_identity(
                            user_id,
                            member['onPremisesDomainName'],
                            member['onPremisesSecurityIdentifier'],
                        )
                        update_identity(user_name, identity)
                    except Exception:
                        logger.exception('Exception in member {}'.format(member))

            except Exception:
                logger.exception('Exception in processing group {}'.format(group))

    except Exception:
        logger.exception('Exception in processing group identity {}'.format(group_identity))
