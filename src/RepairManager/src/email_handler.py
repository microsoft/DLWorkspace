#!/usr/bin/env python3

import argparse
import logging
import smtplib

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


logger = logging.getLogger(__name__)


class EmailHandler(object):
    def __init__(self, smtp):
        self.smtp_url = smtp.get("smtp_url", "localhost:9095")
        self.smtp_from = smtp.get("smtp_from")
        self.username = smtp.get("username")
        self.password = smtp.get("password")

    def send(self, subject, to, body):
        message = MIMEMultipart()
        message["Subject"] = subject
        message["From"] = self.smtp_from
        message["to"] = to
        message.attach(MIMEText(body, 'html'))

        try:
            with smtplib.SMTP(self.smtp_url) as server:
                if self.username and self.password:
                    server.starttls()
                    server.login(self.username, self.password)
                server.send_message(message)
                logger.info("successfully sent email %s to %s", subject, to)
        except smtplib.SMTPAuthenticationError:
            logger.error(
                "The server didn\'t accept the user/password combination.")
        except smtplib.SMTPServerDisconnected:
            logger.error("Server unexpectedly disconnected")
        except smtplib.SMTPException:
            logger.exception("STMP exception")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--smtp_url",
                        "-u",
                        help="Url to SMTP server",
                        default="localhost:9095")
    parser.add_argument("--smtp_from",
                        "-s",
                        help="Email sender",
                        required=True)
    parser.add_argument("--dashboard",
                        "-d",
                        help="Dashboard url",
                        required=True)
    parser.add_argument("--cluster",
                        "-c",
                        help="Cluster name",
                        required=True)
    parser.add_argument("--vc_name",
                        "-vc",
                        help="VC name",
                        required=True)
    parser.add_argument("--job_id",
                        "-j",
                        help="Job id",
                        required=True)
    parser.add_argument("--username",
                        "-o",
                        help="Job owner",
                        required=True)
    args = parser.parse_args()

    smtp = {
        "smtp_url": args.smtp_url,
        "smtp_from": args.smtp_from,
    }

    handler = EmailHandler(smtp)

    subject = "[DLTS Job Alert][%s/%s] %s is running on an unhealthy node(s)" % \
              (args.vc_name, args.cluster, args.job_id)
    job_link = "https://%s/jobs/%s/%s" % \
               (args.dashboard, args.cluster, args.job_id)
    msg = "Your job <a href=%s>%s</a> is running on an unhealthy node %s (%s). " % \
          (job_link, args.job_id, "dummynode", "dummy reason")
    msg += "Please check if it is still running as expected. "
    msg += "Kill/finish it as soon as possible to expedite node(s) repair."
    body = "<p>%s</p>" % msg
    handler.send(subject, args.username, body)
