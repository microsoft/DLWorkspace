import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from action_abc import Action
from utils import k8s_util


class SendAlertAction(Action):
    def __init__(self, alert_handler):
        self.action_logger = logging.getLogger('activity')
        self.alert_handler = alert_handler

    def execute(self, message, dry_run=False, additional_log=None):
        if not dry_run:
            self.alert_handler.send_alert(message)

        if additional_log is None:
            additional_log = {}
        self.action_logger.info({
            "action": "send alert",
            "dry_run": dry_run,
            "email_to": message.to,
            "email_cc": message.cc,
            "message": message.subject,
            **additional_log
        })
