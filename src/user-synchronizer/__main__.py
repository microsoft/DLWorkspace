# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from os import environ
import sys
from sys import stdout

from yaml import safe_load

from logging import getLogger, FileHandler, StreamHandler
from restfulapi import iter_acls, update_identity
from microsoft_graph import (
    build_oauth,
    iter_groups_by_mail,
    get_user,
    iter_user_member_of,
    iter_group_member_of,
    iter_group_members,
)

logger = getLogger(__name__)

# Read environment variables
domain_offset_file = environ.get('DOMAIN_OFFSET_FILE', None)
restfulapi_url = environ['RESTFULAPI_URL']
tenant_id = environ['TENANT_ID']
client_id = environ['CLIENT_ID']
client_secret = environ['CLIENT_SECRET']

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


def cache_processed_member(func):
    id_cache = set()

    def wrapped(oauth, member):
        if member['id'] in id_cache:
            logger.info('Already processed {}, skip.'.format(
                member['displayName']))
            return

        try:
            func(oauth, member)
        except Exception:
            logger.exception('Exception in process {}'.format(member))
        else:
            id_cache.add(member['id'])

    return wrapped


@cache_processed_member
def process_user(oauth, user):
    ''' process user '''

    if user['onPremisesDomainName'] is None:
        return
    if user['onPremisesSecurityIdentifier'] is None:
        return

    uid = add_domain_offset(user['onPremisesDomainName'],
                            user['onPremisesSecurityIdentifier'])
    gid = add_domain_offset(user['onPremisesDomainName'], '513')
    groups = [str(gid)]

    for member_of_group in iter_user_member_of(oauth, user['id'], [
            'id',
            'displayName',
            'onPremisesDomainName',
            'onPremisesSecurityIdentifier',
    ]):
        try:
            if member_of_group['onPremisesDomainName'] is None:
                continue
            if member_of_group['onPremisesSecurityIdentifier'] is None:
                continue

            member_of_group_id = add_domain_offset(
                member_of_group['onPremisesDomainName'],
                member_of_group['onPremisesSecurityIdentifier'])
            groups.append(str(member_of_group_id))
        except Exception:
            logger.exception('Exception in processing group', member_of_group)

    update_identity(restfulapi_url, user['userPrincipalName'], uid, gid, groups)


@cache_processed_member
def process_group(oauth, group):
    ''' process group '''

    if group['onPremisesDomainName'] is None:
        return
    if group['onPremisesSecurityIdentifier'] is None:
        return

    uid = gid = add_domain_offset(group['onPremisesDomainName'],
                                  group['onPremisesSecurityIdentifier'])
    groups = [str(gid)]

    for member_of_group in iter_group_member_of(oauth, group['id'], [
            'id',
            'displayName',
            'mail',
            'onPremisesDomainName',
            'onPremisesSecurityIdentifier',
    ]):
        try:
            if member_of_group['onPremisesDomainName'] is None:
                continue
            if member_of_group['onPremisesSecurityIdentifier'] is None:
                continue

            member_of_group_id = add_domain_offset(
                member_of_group['onPremisesDomainName'],
                member_of_group['onPremisesSecurityIdentifier'])
            groups.append(str(member_of_group_id))
        except Exception:
            logger.exception('Exception in processing group', member_of_group)

    update_identity(restfulapi_url, group['mail'], uid, gid, groups)

    try:
        for member in iter_group_members(oauth, group['id'], [
                'id',
                'displayName',
                'userPrincipalName',
                'onPremisesDomainName',
                'onPremisesSecurityIdentifier',
        ]):
            if member['@odata.type'] == '#microsoft.graph.user':
                process_user(oauth, member)
            # elif member['@odata.type'] == '#microsoft.graph.group':
            #     process_group(oauth, member)
            else:
                logger.warning('Skip {}'.format(member['displayName']))
    except Exception:
        logger.exception('Exception in process group members {}'.format(member))


def main():
    has_exception = False

    oauth = build_oauth(tenant_id, client_id, client_secret)

    for acl in iter_acls(restfulapi_url):
        try:
            acl_name = acl['identityName']

            for group in iter_groups_by_mail(oauth, acl_name, [
                    'id',
                    'displayName',
                    'mail',
                    'onPremisesDomainName',
                    'onPremisesSecurityIdentifier',
            ]):
                process_group(oauth, group)

            user = get_user(oauth, acl_name, [
                'id',
                'displayName',
                'userPrincipalName',
                'onPremisesDomainName',
                'onPremisesSecurityIdentifier',
            ])
            if user is not None:
                process_user(oauth, user)

        except Exception:
            logger.exception('Exception in processing ACL {}'.format(acl))
            has_exception = True
    if has_exception:
        return 1
    else:
        return 0


def config_logging():
    log_level = environ.get('LOG_LEVEL', 'INFO')
    log_file = environ.get('LOG_FILE')
    root_logger = getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(StreamHandler(stdout))
    if log_file is not None:
        root_logger.addHandler(FileHandler(log_file))


if __name__ == "__main__":
    config_logging()
    sys.exit(main())
