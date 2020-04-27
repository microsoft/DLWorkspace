import smtplib
import logging
import yaml
import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


class EmailHandler():

    def __init__(self):
        self.config=self.load_config()

    def load_config(self):
        with open('/etc/RepairManager/config/email-config.yaml', 'r') as file:
            return yaml.safe_load(file)

    def send(self, message):
        message['From'] = self.config['sender']

        try:
            with smtplib.SMTP(self.config['smtp_url']) as server:
                server.starttls()
                server.login(self.config['login'], self.config['password'])
                server.send_message(message)
                logging.info(f"Email sent to {message['To']}: {message['Subject']}")
        except smtplib.SMTPAuthenticationError:
            logging.warning('The server didn\'t accept the user\\password combination.')
        except smtplib.SMTPServerDisconnected:
            logging.warning('Server unexpectedly disconnected')
        except smtplib.SMTPException as e:
            logging.exception('SMTP error occurred: ' + str(e))
