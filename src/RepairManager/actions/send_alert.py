import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from action_abc import Action
from utils import k8s_util


class SendAlert(Action):

    def __init__(self, activity_logger, alert_handler):
        self.activity_logger = activity_logger
        self.alert_handler = alert_handler

    def execute(self, message, additional_log=None):
        self.alert_handler.send_alert(message)

        if additional_log is None:
            additional_log = {}
        self.activity_logger.info({
            "action": "send alert",
            "email": message['To'],
            "message": message['Subject'],
            **additional_log
        })
