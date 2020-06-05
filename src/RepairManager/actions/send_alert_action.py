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
        default_email = self.alert_handler.email_handler.config[
            'default_recepient']
        if 'To' not in message:
            message['To'] = default_email
        else:
            message['CC'] = default_email

        if not dry_run:
            self.alert_handler.send_alert(message)

        if additional_log is None:
            additional_log = {}
        self.action_logger.info({
            "action": "send alert",
            "dry_run": dry_run,
            "email_to": message['To'],
            "email_cc": message['CC'],
            "message": message['Subject'],
            **additional_log
        })
