#!/usr/bin/env python3

import smtplib
import logging

logger = logging.getLogger(__name__)


class EmailHandler(object):
    def __init__(self, smtp_url, sender, username=None, password=None):
        self.smtp_url = smtp_url
        self.sender = sender
        self.username = username
        self.password = password

    def send(self, message):
        message["From"] = self.sender

        try:
            with smtplib.SMTP(self.smtp_url) as server:
                if self.username and self.password:
                    server.starttls()
                    server.login(self.username, self.password)
                server.send_message(message)
        except smtplib.SMTPAuthenticationError:
            logger.error(
                "The server didn\'t accept the user/password combination.")
        except smtplib.SMTPServerDisconnected:
            logger.error("Server unexpectedly disconnected")
        except smtplib.SMTPException:
            logger.exception("STMP exception")
