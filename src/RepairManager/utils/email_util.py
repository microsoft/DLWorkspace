import smtplib
import logging
import yaml
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests

logger = logging.getLogger(__name__)

DEFAULT_ENCODING = "utf-8"


class EmailMessage(object):
    def __init__(self, to, cc, subject, body, body_type):
        self.to = to # , seperated list of receipt or None
        self.cc = cc # , seperated list of receipt or None
        self.subject = subject # plain text
        self.body = body # plain or html text
        self.body_type = body_type # "plain" or "html"

    def to_json(self, default_recepient):
        result = {
            "Subject": self.subject,
            "Body": self.body,
            "BodyType": self.body_type,
        }
        if self.to is None:
            result["To"] = default_recepient
        else:
            result["CC"] = default_recepient
        return result

    def to_mime_message(self, default_recepient):
        msg = MIMEMultipart()
        if self.to is None:
            msg["To"] = default_recepient
        else:
            msg["CC"] = default_recepient
        msg["Subject"] = self.subject
        body = MIMEText(self.body.encode(DEFAULT_ENCODING),
                        self.body_type,
                        _charset=DEFAULT_ENCODING)
        msg.attach(body)
        return msg


class EmailHandler():
    def __init__(self):
        self.config = self.load_config()
        self.default_recepient = self.config["default_recepient"]

    def load_config(self):
        with open('/etc/RepairManager/config/email-config.yaml', 'r') as file:
            return yaml.safe_load(file)

    def _send_via_smtp(self, message):
        msg = message.to_mime_message(self.default_recepient)
        msg['From'] = self.config['sender']

        try:
            with smtplib.SMTP(self.config['smtp_url']) as server:
                server.starttls()
                server.login(self.config['login'], self.config['password'])
                server.send_message(message)
                logger.info(
                    f"Email sent to {message['To']}: {message['Subject']}")
        except smtplib.SMTPAuthenticationError:
            logger.warning(
                'The server didn\'t accept the user\\password combination.')
        except smtplib.SMTPServerDisconnected:
            logger.warning('Server unexpectedly disconnected')
        except smtplib.SMTPException as e:
            logger.exception('SMTP error occurred: ' + str(e))

    def _send_via_email_sender(self, message):
        msg = message.to_json(self.default_recepient)
        succ = False
        resp = None

        for _ in range(3):
            try:
                resp = requests.post(self.config["email_sender_url"],
                                     json=msg,
                                     timeout=3)
                if resp.status_code == 201:
                    succ = True
                    break
            except requests.exceptions.Timeout:
                time.sleep(1)
            except Exception:
                logger.exception("failed to post to email_sender, retry")
                time.sleep(1)

        if not succ:
            logger.error(
                "failed to post email to email_sender %s, code %s, resp %s. Drop email %s",
                self.config["email_sender_url"],
                None if resp is None else resp.status_code, resp, msg)

    def send(self, message):
        if self.config.get("email_sender_url") is not None:
            self._send_via_email_sender(message)
        elif self.config.get("smtp_url") is not None:
            self._send_via_smtp(message)
        else:
            logger.warning("no email method configured, drop message %s",
                           message.to_json(self.default_recepient))
