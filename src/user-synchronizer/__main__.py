# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from os import environ

from yaml import safe_load

from logger import logger
from restfulapi import iter_acls, update_identity
from microsoft_graph import (
    iter_groups_by_mail,
    get_user,
    iter_user_member_of,
    iter_group_member_of,
    iter_group_members,
)

# Read environment variables
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


def cache_processed_member(func):
    id_cache = set()

    def wrapped(member):
        if member['id'] in id_cache:
            logger.info('Already processed {}, skip.'.format(member['displayName']))
            return

        try:
            func(member)
        except Exception:
            logger.exception('Exception in process {}'.format(member))
        else:
            id_cache.add(member['id'])

    return wrapped


@cache_processed_member
def process_user(user):
    ''' process user '''

    if user['onPremisesDomainName'] is None:
        return
    if user['onPremisesSecurityIdentifier'] is None:
        return

    uid = add_domain_offset(
        user['onPremisesDomainName'],
        user['onPremisesSecurityIdentifier']
    )
    gid = add_domain_offset(
        user['onPremisesDomainName'],
        '513'
    )
    groups = [str(gid)]

    for member_of_group in iter_user_member_of(user['id'], [
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
                member_of_group['onPremisesSecurityIdentifier']
            )
            groups.append(str(member_of_group_id))
        except Exception:
            logger.exception('Exception in processing group', member_of_group)

    update_identity(user['userPrincipalName'], uid, gid, groups)


@cache_processed_member
def process_group(group):
    ''' process group '''

    if group['onPremisesDomainName'] is None:
        return
    if group['onPremisesSecurityIdentifier'] is None:
        return

    uid = gid = add_domain_offset(
        group['onPremisesDomainName'],
        group['onPremisesSecurityIdentifier']
    )
    groups = [str(gid)]

    for member_of_group in iter_group_member_of(group['id'], [
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
                member_of_group['onPremisesSecurityIdentifier']
            )
            groups.append(str(member_of_group_id))
        except Exception:
            logger.exception('Exception in processing group', member_of_group)

    update_identity(group['mail'], uid, gid, groups)

    try:
        for member in iter_group_members(group['id'], [
            'id',
            'displayName',
            'userPrincipalName',
            'onPremisesDomainName',
            'onPremisesSecurityIdentifier',
        ]):
            if member['@odata.type'] == '#microsoft.graph.user':
                process_user(member)
            # elif member['@odata.type'] == '#microsoft.graph.group':
            #     process_group(member)
            else:
                logger.warning('Skip {}'.format(member['displayName']))
    except Exception:
        logger.exception('Exception in process group members {}'.format(member))


def main():
    for acl in iter_acls():
        try:
            acl_name = acl['identityName']

            for group in iter_groups_by_mail(acl_name, [
                'id',
                'displayName',
                'mail',
                'onPremisesDomainName',
                'onPremisesSecurityIdentifier',
            ]):
                process_group(group)

            user = get_user(acl_name, [
                'id',
                'displayName',
                'userPrincipalName',
                'onPremisesDomainName',
                'onPremisesSecurityIdentifier',
            ])
            if user is not None:
                process_user(user)

        except Exception:
            logger.exception('Exception in processing ACL {}'.format(acl))


if __name__ == "__main__":
    main()
