# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from json import dumps
from os import environ

from requests import get
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from logger import logger


def generate_ssh_key_pair():
    key = rsa.generate_private_key(public_exponent=65537,
                                   key_size=2048,
                                   backend=default_backend())

    private_key = key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption()).decode("utf-8")
    public_key = key.public_key().public_bytes(
        serialization.Encoding.OpenSSH,
        serialization.PublicFormat.OpenSSH).decode("utf-8")
    return private_key, public_key


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
