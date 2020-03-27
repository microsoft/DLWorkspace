# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from json import dumps
import os
import logging
import uuid

from requests import get

logger = logging.getLogger(__name__)


def generate_ssh_key_pair():
    name = str(uuid.uuid4())

    os.system("ssh-keygen -t rsa -b 4096 -f %s -P ''" % name)

    with open(name) as f:
        private = f.read()

    with open(name + ".pub") as f:
        public = f.read()

    return private, public


def iter_acls(restfulapi_url):
    ''' Iterate group identities from RestfulAPI '''
    response = get(restfulapi_url + '/GetAllACL')
    response.raise_for_status()
    response_json = response.json()
    result = response_json['result']

    logger.info('Fetched {} ACLs'.format(len(result)))

    yield from result


def update_identity(restfulapi_url, user_name, uid, gid, groups):
    ''' Update identity info to the cluster '''
    private, public = generate_ssh_key_pair()
    params = {
        'userName': user_name,
        'uid': int(uid),
        'gid': int(gid),
        'groups': dumps(groups, separators=(',', ':')),
        'private_key': private,
        'public_key': public,
    }
    response = get(restfulapi_url + '/AddUser', params=params)
    response.raise_for_status()

    logger.info('Updated {} to cluster'.format(user_name))


if __name__ == "__main__":
    print(generate_ssh_key_pair())
