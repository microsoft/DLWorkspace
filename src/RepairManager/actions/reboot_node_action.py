import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import logging
import requests
from action_abc import Action


class RebootNodeAction(Action):
    def __init__(self):
        self.action_logger = logging.getLogger('activity')

    def execute(self, node_name, etcd_config, dry_run=False):
        etcd_url = etcd_url = f'{etcd_config["advertise-client-urls"]}/v2/keys'
        key = f'{node_name}/reboot'
        success = False
        try:
            if dry_run:
                value = 'DryRun'
            else:
                value = 'True'

            response = requests.put(f'{etcd_url}/{key}', data={'value': value})
            r_json = response.json()
            if  "node" in r_json and \
                r_json["node"]["key"] == f'/{key}' and \
                r_json["node"]["value"] == value:
                success = True

        except:
            logging.exception(
                f'Error sending reboot signal for node {node_name}')

        self.action_logger.info({
            "action": "reboot",
            "node": node_name,
            "dry_run": dry_run,
            "success": success
        })

        return success
