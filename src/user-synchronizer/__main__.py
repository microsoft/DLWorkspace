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

# Synchronize
url_template = 'https://graph.microsoft.com/v1.0/groups/{}/members'
database = connect(database_url)
table = database['identity']
for group_id in groups_id:
    try:
        # Get members in the group
        url = url_template.format(group_id)
        groups_response = oauth.get(url)
        groups_response.raise_for_status()
        members = groups_response.json()['value']
        logger.info('Fetch {} members in group {}'.format(
            len(members), group_id
        ))

        for member in members:
            try:
                if 'mail' not in member:
                    logger.warn('Member has no mail: {}'.format(member))
                    continue
                mail = member['mail']

                # Get identity info of the member.
                params = {'userName': mail}
                winbind_response = get(winbind_url, params=params)
                identity = winbind_response.json()
                logger.info('Finish fetch {} from winbind'.format(mail))

                # Update identity in database
                row = {
                    'identityName': mail,
                    'uid': int(identity['uid']),
                    'gid': int(identity['gid']),
                    'groups': dumps(identity['groups']),
                }
                table.upsert(row, keys=['identityName'])
                logger.info('Finish sync member {}'.format(mail))
            except Exception:
                logger.exception('Exception in member {}'.format(member))

        logger.info('Finish group {}'.format(group_id))
    except Exception:
        logger.exception('Exception in group {}'.format(group_id))
