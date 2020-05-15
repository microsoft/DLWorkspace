#!/usr/bin/env python3

import json
import logging
import logging.config
import requests
import smtplib
import subprocess

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.charset import Charset, BASE64
from email.mime.nonmultipart import MIMENonMultipart

logger = logging.getLogger(__name__)

DATETIME_FMT = "%Y/%m/%d %H:%M:%S"
ENCODING = "utf-8"
K = 2**10
M = 2**20
G = 2**30

DAY = 86400

MAX_NODES_IN_REPORT = 5000


def override(func):
    return func


def df(path):
    """Returns the used percentage number for the specified scan_point.

    Args:
        path: Path

    Returns:
        Used percentage number of the device mount for path or None otherwise.
    """
    try:
        df_cmd = subprocess.Popen(["df", path], stdout=subprocess.PIPE)
        output = df_cmd.communicate(timeout=3)[0].decode()
        _, _, _, _, percent, _ = output.split("\n")[1].split()
        return float(percent.strip("%"))
    except subprocess.TimeoutExpired:
        logger.warning("df %s timeout.", path)
    except Exception:
        logger.exception("\"df %s\" failed.", path, exc_info=True)


def get_uid_to_user(restful_url):
    """Gets uid -> user mapping from restful url"""
    query_url = restful_url + "/GetAllUsers"
    resp = requests.get(query_url)
    if resp.status_code != 200:
        logger.warning("Querying %s failed.", query_url)
        return {}

    data = json.loads(resp.text)
    uid_to_user = {}
    for item in data:
        try:
            uid = int(item[1])
            user = item[0]
            uid_to_user[uid] = user
        except Exception as e:
            logger.warning("Parsing %s failed: %s", item, e)
    return uid_to_user


def send_email(smtp, recipients, cc, subject, content, csv_reports):
    """Sends an email with attachment.
    Refer to https://gist.github.com/BietteMaxime/f75ae41f7b4557274a9f

    Args:
        smtp: A dictionary containing smtp info:
            - smtp_url
            - smtp_auth_username # optional
            - smtp_auth_password # optional
            - smtp_from
        recipients: To whom to send the email.
        cc: To whom to cc the email.
        subject: Email subject.
        content: Email body content
        csv_reports: List of dictionaries containing "filename", "data" to
            construct CSV attachments.

    Returns:
        None
    """
    if not isinstance(smtp, dict):
        logger.warning("smtp is not a dictionary. Skip.")
        return

    sender = smtp.get("smtp_from", None)
    smtp_url = smtp.get("smtp_url", None)
    smtp_auth_username = smtp.get("smtp_auth_username", None)
    smtp_auth_password = smtp.get("smtp_auth_password", None)
    if sender is None or smtp_url is None:
        logger.warning("Some fields in smtp %s is None. Skip.", smtp)
        return

    # Create message container - the correct MIME type is multipart/mixed
    # to allow attachment.
    full_email = MIMEMultipart("mixed")
    full_email["Subject"] = subject
    full_email["From"] = sender
    full_email["To"] = ", ".join(recipients)
    full_email["CC"] = ", ".join(cc)

    # Create the body of the message (a plain-text version).
    content = content.encode(ENCODING)
    content = MIMEText(content, "plain", _charset=ENCODING)
    body = MIMEMultipart("alternative")
    body.attach(content)
    full_email.attach(body)

    # Create the attachment of the message in text/csv.
    for report in csv_reports:
        attachment = MIMENonMultipart("text", "csv", charset=ENCODING)
        attachment.add_header("Content-Disposition",
                              "attachment",
                              filename=report["filename"])
        cs = Charset(ENCODING)
        cs.body_encoding = BASE64
        attachment.set_payload(report["data"].encode(ENCODING), charset=cs)
        full_email.attach(attachment)

    try:
        with smtplib.SMTP(smtp_url) as server:
            if smtp_auth_username is not None and smtp_auth_password is not None:
                server.starttls()
                server.login(smtp_auth_username, smtp_auth_password)

            receivers = recipients + cc
            server.sendmail(sender, receivers, full_email.as_string())
            logger.info("Successfully sent email to %s and cc %s",
                        ", ".join(recipients), ", ".join(cc))
    except smtplib.SMTPAuthenticationError:
        logger.warning("The server didn\'t accept the user\\password "
                       "combination.")
    except smtplib.SMTPServerDisconnected:
        logger.warning("Server unexpectedly disconnected")
    except smtplib.SMTPException as e:
        logger.exception("SMTP error occurred: %s", e)


def bytes2human_readable(value):
    if value // G > 0:
        return "%dG" % (value // G)
    if value // M > 0:
        return "%dM" % (value // M)
    if value // K > 0:
        return "%dK" % (value // K)
    return "%d" % value


def ancestor_exists(path, ancestors):
    for ancestor in ancestors:
        if path.startswith(ancestor):
            return True
    return False


def remove_descendents(path, ancestors):
    new_ancestors = set()
    for ancestor in ancestors:
        if ancestor.startswith(path):
            continue
        new_ancestors.add(ancestor)
    new_ancestors.add(path)
    return new_ancestors


def keep_ancestor_paths(paths):
    ancestors = set()
    for path in paths:
        if ancestor_exists(path, ancestors):
            continue
        ancestors = remove_descendents(path, ancestors)
        ancestors.add(path)
    return sorted(list(ancestors))
