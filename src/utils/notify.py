#!/usr/bin/env python3

import threading
import time
import logging
import json
import smtplib

from queue import Queue
from queue import Empty

import requests

logger = logging.getLogger(__name__)


class NotifyMsg(object):
    def __init__(self, email, alert_name):
        self.email = email
        self.alert_name = alert_name

    def labels(self):
        raise NotImplementedError()

    def subject(self):
        raise NotImplementedError()

    def body(self):
        return self.subject()


class JobStateChangedMsg(NotifyMsg):
    def __init__(self, email, alert_name, job_name, job_state):
        super(JobStateChangedMsg, self).__init__(email, alert_name)
        self.job_name = job_name
        self.job_state = job_state

    def labels(self):
        return {"job_name": self.job_name, "job_state": self.job_state}

    def subject(self):
        return "Your job %s has changed to state of %s" % (self.job_name,
                                                           self.job_state)


class JobKilledMsg(NotifyMsg):
    def __init__(self, email, alert_name, job_name, reason):
        super(JobKilledMsg, self).__init__(email, alert_name)
        self.job_name = job_name
        self.reason = reason

    def labels(self):
        return {"job_name": self.job_name, "reason": self.reason}

    def subject(self):
        return "Your job %s was killed" % (self.job_name)


def new_job_state_change_message(email, job_name, state):
    return JobStateChangedMsg(email, "job-state-changed", job_name, state)


def new_job_killed_message(email, job_name, reason):
    return JobKilledMsg(email, "kill-job", job_name, reason)


class Notifier(object):
    def __init__(self, config):
        self.queue = Queue()
        self.running = False
        self.thread = None

        self.cluster = None
        self.alert_manager_url = None
        self.smtp_url = self.smtp_from = self.smtp_auth_name = self.smtp_auth_pass = None

        if config is not None and "notifier" in config:
            notifier_config = config["notifier"]

            self.cluster = notifier_config.get("cluster")
            self.smtp_url = notifier_config.get("smtp-url")
            self.smtp_from = notifier_config.get("smtp-from")
            self.smtp_auth_name = notifier_config.get("smtp-auth-username")
            self.smtp_auth_pass = notifier_config.get("smtp-auth-password")

            alert_manager_url = notifier_config.get("alert-manager-url")
            if alert_manager_url is not None and len(alert_manager_url) > 0:
                if alert_manager_url[-1] == "/":
                    self.alert_manager_url = alert_manager_url + "api/v1/alerts"
                else:
                    self.alert_manager_url = alert_manager_url + "/api/v1/alerts"

        if self.cluster is None or \
                self.alert_manager_url is None and (
                    self.smtp_url is None or
                    self.smtp_from is None or
                    self.smtp_auth_name is None or
                    self.smtp_auth_pass is None):
            logger.warning("Notifier not configured")

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.process, name="notifier")
            self.thread.start()

    def stop(self):
        if self.running:
            self.running = False
            self.thread.join()
            self.thread = None

    def notify(self, msg):
        self.queue.put(msg)

    def process(self):
        while self.running:
            try:
                msg = self.queue.get(block=True, timeout=1) # 1s timeout
            except Empty:
                continue

            retry_count = 0
            sent = False

            while retry_count < 3:
                if self.send(msg):
                    sent = True
                    break
                time.sleep(0.2)
                retry_count += 1

            if not sent:
                logger.error("failed to send out, discard msg: %s", msg)

    def send(self, msg):
        subject = msg.subject()

        try:
            if self.alert_manager_url is not None:
                labels = msg.labels()
                labels.update({
                    "alertname": msg.alert_name,
                    "type": "user_alert",
                    "cluster": self.cluster,
                    "user_email": msg.email,
                    "subject": subject,
                })

                resp = requests.post(self.alert_manager_url,
                                     timeout=5,
                                     data=json.dumps([{
                                         "labels": labels
                                     }]))
                resp.raise_for_status()
                return True
            elif self.smtp_url is not None and \
                    self.smtp_from is not None and \
                    self.smtp_auth_name is not None and \
                    self.smtp_auth_pass is not None:
                smtp_send_email(self.smtp_url, self.smtp_from,
                                self.smtp_auth_name, self.smtp_auth_pass,
                                msg.email, subject, msg.body())
                return True
            else:
                # not configured, discard message
                return True
        except Exception as e:
            logger.exception("sending email failed")
            return False


def smtp_send_email(smtp_url, smtp_from, smtp_auth_name, smtp_auth_pass, to,
                    subject, body):
    msg = "From: %s\r\nTo: %s\r\nSubject: %s\r\n\r\n%s" % (smtp_from, to,
                                                           subject, body)
    conn = smtplib.SMTP(smtp_url)
    conn.starttls()
    conn.login(smtp_auth_name, smtp_auth_pass)
    conn.sendmail(smtp_from, to, msg)


if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s',
                        level=logging.INFO)
    notifier = Notifier({
        "notifier": {
            "cluster": "local",
            "alert-manager-url": "http://localhost:9093/alert-manager"
        }
    })
    notifier.start()

    notifier.notify(
        new_job_state_change_message("dixu@microsoft.com", "job-id", "stopped"))
    notifier.stop()
