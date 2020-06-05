import smtplib
import logging
import yaml
import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


class EmailHandler():
    def __init__(self):
        self.config = self.load_config()

    def load_config(self):
        with open('/etc/RepairManager/config/email-config.yaml', 'r') as file:
            return yaml.safe_load(file)

    def _configured(self, key):
        return self.config.get(key) is not None

    def send(self, message):
        message['From'] = self.config['sender']

        try:
            with smtplib.SMTP(self.config['smtp_url']) as server:
                if self._configured("login") and self._configured('password'):
                    server.starttls()
                    server.login(self.config['login'], self.config['password'])
                server.send_message(message)
                logging.info(
                    f"Email sent to {message['To']}: {message['Subject']}")
        except smtplib.SMTPAuthenticationError:
            logging.warning(
                'The server didn\'t accept the user\\password combination.')
        except smtplib.SMTPServerDisconnected:
            logging.warning('Server unexpectedly disconnected')
        except smtplib.SMTPException as e:
            logging.exception('SMTP error occurred: ' + str(e))
