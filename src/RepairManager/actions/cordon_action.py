import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import logging
from action_abc import Action
from utils import k8s_util

class CordonAction(Action):

    def __init__(self):
        self.action_logger = logging.getLogger('activity')

    def execute(self, node_name, dry_run=False):
        cordon_status = k8s_util.cordon_node(node_name, dry_run=dry_run)

        self.action_logger.info({
            "action": "cordon",
            "node": node_name,
            "dry_run": dry_run,
            "status": cordon_status
            })
        return cordon_status
