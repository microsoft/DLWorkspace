import smtplib
import logging
import yaml
import datetime

class EmailHandler():

    def __init__(self):
        self.config=self.load_config()
        self.monitor_alerts = {}

    def load_config(self):
        with open('./config/email-config.yaml', 'r') as file:
            return yaml.safe_load(file)

    def send(self, subject, body):
        message = "From: %s\r\nTo: %s\r\nSubject: %s\r\n\r\n%s" % (self.config['sender'], self.config['receiver'], subject, body)

        try:
            with smtplib.SMTP(self.config['smtp_url']) as server:
                server.starttls()
                server.login(self.config['login'], self.config['password'])
                server.sendmail(self.config['sender'], self.config['receiver'], message)
                logging.info('Email Sent')
        except smtplib.SMTPAuthenticationError:
            logging.warning('The server didn\'t accept the user\\password combination.')
        except smtplib.SMTPServerDisconnected:
            logging.warning('Server unexpectedly disconnected')
        except smtplib.SMTPException as e:
            logging.exception('SMTP error occurred: ' + str(e))

    def handle_email_alert(self, subject, body):
        time_now = datetime.datetime.now()

        # to avoid email clutter, send email based on configured alert wait time
        for alert in self.monitor_alerts:
            time_start = self.monitor_alerts[alert]
            time_delta = datetime.timedelta(hours=self.config['alert_wait_time'])
            wait_time_reached = time_now - time_start > time_delta

            if wait_time_reached:

                if alert == body:
                    self.send(subject, body)
                    self.monitor_alerts[alert] = datetime.datetime.now()

                else:
                    self.monitor_alerts.pop(alert)

        if body not in self.monitor_alerts:
            self.send(subject, body)
            self.monitor_alerts[body] = datetime.datetime.now()  