import smtplib
import logging
import yaml
import datetime

class EmailHandler():

    def __init__(self):
        self.config=self.load_config()
        self.ecc_alert_cache=[]
        self.ecc_alert_reminder = None

    def load_config(self):
        with open('./config/email-config.yaml', 'r') as file:
            return yaml.safe_load(file)

    def send(self, subject, body, additional_recipients=None):
        recepients = self.config['receiver']
        if additional_recipients is not None:
            recepients = recepients + additional_recipients

        message = (
            f"From: {self.config['sender']}\r\n"
            f"To: {';'.join(recepients)}\r\n"
            f"MIME-Version: 1.0\r\n"
            f"Content-type: text/html\r\n"
            f"Subject: {subject}\r\n\r\n{body}"
        )

        try:
            with smtplib.SMTP(self.config['smtp_url']) as server:
                server.starttls()
                server.login(self.config['login'], self.config['password'])
                server.sendmail(self.config['sender'], recepients, message)
                logging.info(f"Email sent to {', '.join(recepients)}")
        except smtplib.SMTPAuthenticationError:
            logging.warning('The server didn\'t accept the user\\password combination.')
        except smtplib.SMTPServerDisconnected:
            logging.warning('Server unexpectedly disconnected')
        except smtplib.SMTPException as e:
            logging.exception('SMTP error occurred: ' + str(e))

    def handle_ecc_email_alert(self, subject, body, ecc_nodes, action_taken, additional_recipients=None):
        if ecc_nodes is None:
            ecc_nodes = []

        # if a new node found to have ecc error, send email
        if not set(ecc_nodes).issubset(self.ecc_alert_cache):
            self.ecc_alert_reminder = datetime.datetime.now() + datetime.timedelta(seconds=self.config['alert_wait_seconds'])
            self.send(subject, body, additional_recipients)
            # TODO: send email to individual job owners on each new node

        # if ecc errors remain on nodes after configured alert wait time, resend email 
        # or if any action is taken on a node
        elif self.ecc_alert_reminder < datetime.datetime.now() \
        or action_taken:
            self.ecc_alert_reminder = datetime.datetime.now() + datetime.timedelta(seconds=self.config['alert_wait_seconds'])
            self.send(subject, body, additional_recipients)

        self.ecc_alert_cache = ecc_nodes

    def clear_ecc_alert_cache(self):
        self.ecc_alert_cache = []