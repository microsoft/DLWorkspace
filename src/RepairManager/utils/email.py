import smtplib
import logging
import yaml
import datetime
from cachetools import TTLCache

class EmailHandler():

    def __init__(self):
        self.config=self.load_config()
        self.alert_cache=TTLCache(maxsize=1000, ttl=self.config['alert_wait_seconds'])

    def load_config(self):
        with open('./config/email-config.yaml', 'r') as file:
            return yaml.safe_load(file)

    def send(self, subject, body):
        message = f"From: {self.config['sender']}\r\nTo: {';'.join(self.config['receiver'])}\r\nSubject: {subject}\r\n\r\n{body}"

        try:
            with smtplib.SMTP(self.config['smtp_url']) as server:
                server.starttls()
                server.login(self.config['login'], self.config['password'])
                server.sendmail(self.config['sender'], self.config['receiver'], message)
                logging.info(f"Email sent to {', '.join(self.config['receiver'])}")
        except smtplib.SMTPAuthenticationError:
            logging.warning('The server didn\'t accept the user\\password combination.')
        except smtplib.SMTPServerDisconnected:
            logging.warning('Server unexpectedly disconnected')
        except smtplib.SMTPException as e:
            logging.exception('SMTP error occurred: ' + str(e))

    def handle_email_alert(self, subject, body):

        # to avoid email spam, send email based on configured alert wait time
        if body not in self.alert_cache:
            self.send(subject, body)
            self.alert_cache[body] = 1  