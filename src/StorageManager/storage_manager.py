import logging
import time
import os
import subprocess
import smtplib
import requests
import json

from path_tree import PathTree
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.charset import Charset, BASE64
from email.mime.nonmultipart import MIMENonMultipart
from utils import bytes2human_readable, G


ENCODING = "utf-8"


class StorageManager(object):
    """This class implements a storage manager that scans defined scan_points
     on regular basis.

    Attributes:
        logger: Logging tool.
        config: Configuration for StorageManager.
        execution_interval: Number of seconds in between for consecutive runs.
        last_now: The unix epoch time in seconds.
        scan_points: A list of scan point configurations.
    """
    def __init__(self, config, smtp, cluster_name):
        self.logger = logging.getLogger()

        self.config = config
        self.smtp = smtp
        self.cluster_name = cluster_name

        default_restful_url = "http://192.168.255.1:5000"
        self.restful_url = self.config.get("restful_url", default_restful_url)

        self.execution_interval = self.config.get("execution_interval", 86400)
        self.last_now = None
        self.scan_points = self.config.get("scan_points", [])
        assert isinstance(self.scan_points, list)

        self.overweight_threshold = self.config.get("overweight_threshold",
                                                    200 * G)
        self.expiry_days = self.config.get("expiry_days", 31)

        self.logger.info("config: %s", self.config)
        self.logger.info("smtp: %s", self.smtp)
        self.logger.info("cluster_name: %s", self.cluster_name)

    def run(self):
        """Runs a while loop to monitor scan_points."""
        while True:
            if self.last_now is None:
                self.last_now = time.time()

            try:
                self.scan()
            except Exception as e:
                self.logger.error("scan failed with exception %s", e)

            next_scan_time = self.last_now + self.execution_interval
            time2_next_scan = max(0, next_scan_time - time.time())
            self.logger.info("Sleeping for %s sec before next scan.",
                             time2_next_scan)
            time.sleep(time2_next_scan)

            self.last_now = time.time()

    def scan_point_used_percent(self, path):
        """Returns the used percentage number for the specified scan_point.

        Args:
            path: Path of a mount point

        Returns:
            Used percentage number of the scan_point or None otherwise.
        """
        try:
            df = subprocess.Popen(["df", path], stdout=subprocess.PIPE)
            output = df.communicate(timeout=3)[0].decode()
            _, _, _, _, percent, _ = output.split("\n")[1].split()
            return float(percent.strip("%"))
        except subprocess.TimeoutExpired:
            self.logger.warning("df %s timeout.", path)
        except Exception:
            self.logger.exception("Getting used percent for %s failed.", path)

        return None

    def send_email(self, recipients, cc, subject, content, report):
        """Sends an email with attachment.
        Refer to https://gist.github.com/BietteMaxime/f75ae41f7b4557274a9f

        Args:
            recipients: To whom to send the email.
            cc: To whom to cc the email.
            subject: Email subject.
            content: Email body content
            report: A dictionary containing "filename", "data" to construct a
                CSV attachment.

        Returns:
            None
        """
        # Get sender from configuration
        sender = self.smtp["smtp_from"]

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
        attachment = MIMENonMultipart("text", "csv", charset=ENCODING)
        attachment.add_header("Content-Disposition", "attachment",
                              filename=report["filename"])
        cs = Charset(ENCODING)
        cs.body_encoding = BASE64
        attachment.set_payload(report["data"].encode(ENCODING), charset=cs)
        full_email.attach(attachment)

        try:
            with smtplib.SMTP(self.smtp["smtp_url"]) as server:
                server.starttls()

                username = self.smtp["smtp_auth_username"]
                password = self.smtp["smtp_auth_password"]
                server.login(username, password)

                receivers = recipients + cc
                server.sendmail(sender, receivers, full_email.as_string())
                self.logger.info("Successfully sent email to %s and cc %s",
                                 ", ".join(recipients), ", ".join(cc))
        except smtplib.SMTPAuthenticationError:
            self.logger.warning("The server didn\'t accept the user\\password "
                                "combination.")
        except smtplib.SMTPServerDisconnected:
            self.logger.warning("Server unexpectedly disconnected")
        except smtplib.SMTPException as e:
            self.logger.exception("SMTP error occurred: %s", e)

    def get_uid_user(self):
        """Gets uid -> user mapping from restful url"""
        query_url = self.restful_url + "/GetAllUsers"
        resp = requests.get(query_url)
        if resp.status_code != 200:
            self.logger.warning("Querying %s failed.", query_url)
            return {}

        data = json.loads(resp.text)
        uid_user = {}
        for item in data:
            try:
                uid = int(item[1])
                user = item[0]
                uid_user[uid] = user
            except Exception as e:
                self.logger.warning("Parsing %s failed: %s", item, e)
        return uid_user

    def scan(self):
        """Scans each scan_point and finds overweight nodes. Sends alert."""
        uid_user = self.get_uid_user()

        for sp in self.scan_points:
            # device_mount, user_percent_alert_threshold, path must exist
            if "device_mount" not in sp:
                self.logger.warning("device_mount missing in %s. Skip.", sp)
                continue
            device_mount = sp["device_mount"]

            if "path" not in sp:
                self.logger.warning("path missing in %s. Skip.", sp)
                continue
            path = sp["path"]
            alias = sp["alias"] if "alias" in sp else path

            if "used_percent_alert_threshold" not in sp:
                self.logger.warning("user_percent_alert_threshold missing in "
                                    "%s. Setting to 90.", sp)
                sp["used_percent_alert_threshold"] = 90
            used_percent_alert_threshold = \
                float(sp["used_percent_alert_threshold"])

            # Only scan if alert threshold is reached
            used_percent = self.scan_point_used_percent(device_mount)
            if used_percent is None:
                self.logger.warning("used_percent is None. Skip.")
                continue

            if used_percent < used_percent_alert_threshold:
                self.logger.info("%s used percent %s < threshold %s. Skip.",
                                 sp, used_percent, used_percent_alert_threshold)
                continue

            if "overweight_threshold" not in sp:
                self.logger.info("overweight_threshold does not exist in %s. "
                                 "Using parent overweight_threshold %d.",
                                 sp, self.overweight_threshold)
                sp["overweight_threshold"] = self.overweight_threshold

            if "expiry_days" not in sp:
                self.logger.info("expiry_days does not exist in %s. "
                                 "Using parent expiry_days %d.",
                                 sp, self.expiry_days)
                sp["expiry_days"] = self.expiry_days

            if not os.path.exists(sp["path"]):
                self.logger.warning("%s is absent in file system. Skip.", sp)
                continue

            sp["now"] = self.last_now

            self.logger.info("Scanning scan point %s", sp)

            tree = PathTree(sp, uid_user=uid_user)
            tree.walk()

            root = tree.root
            if root is not None:
                self.logger.info("Total number of paths under %s found: %d",
                                 tree.path, root.num_subtree_nodes)
            else:
                self.logger.warning("Tree root for %s is None.", tree.path)

            overweight_nodes = tree.overweight_boundary_nodes

            if self.smtp is None:
                self.logger.warning("stmp is not configured. Skip email.")
                continue

            # Group overweight nodes by user
            user_overweight_nodes = {}
            default_recipient = self.smtp.get("default_recipients", None)
            self.logger.info("default recipient is %s", default_recipient)

            for node in overweight_nodes:
                owner = node.owner
                if owner == "" and default_recipient is None:
                    continue
                elif owner == "" and default_recipient is not None:
                    owner = default_recipient

                if owner not in user_overweight_nodes:
                    user_overweight_nodes[owner] = []
                user_overweight_nodes[owner].append(node)

            for owner, nodes in user_overweight_nodes.items():
                self.logger.info("Overweight (> %d) boundary paths for %s:",
                                 tree.overweight_threshold, owner)
                for node in nodes:
                    self.logger.info(node)

                recipients = owner.split(",")
                cc = self.smtp["cc"].split(",")

                subject = "[%s]" % self.cluster_name
                if "vc" in sp:
                    subject += "[%s]" % sp["vc"]

                subject += "[Storage Manager][%s] Storage usage of %s is at " \
                           "%s%% > %s%%" % \
                           (owner.split("@")[0],
                            alias,
                            used_percent,
                            used_percent_alert_threshold)

                content = "%s storage mountpoint %s usage is at %s%% > %s%%. " \
                          "Full list of your oversized boundary paths (> %s) " \
                          "is in the attached CSV. " \
                          "Please help reduce the size.\n\n" % \
                          (self.cluster_name,
                           alias,
                           used_percent,
                           used_percent_alert_threshold,
                           bytes2human_readable(self.overweight_threshold))

                header = "size_in_bytes,readable_size,owner,path\n"

                preview_len = min(20, len(nodes))
                content += header
                for node in nodes[0:preview_len]:
                    content += "%s,%s,%s,%s\n" % (
                        node.subtree_size,
                        bytes2human_readable(node.subtree_size),
                        node.owner,
                        node.path.replace(path, alias, 1))
                if preview_len < len(nodes):
                    content += "...\n"

                data = header
                for node in nodes:
                    cur_node = "%s,%s,%s,%s\n" % (
                        node.subtree_size,
                        bytes2human_readable(node.subtree_size),
                        node.owner,
                        node.path.replace(path, alias, 1))
                    data += cur_node

                report = {
                    "filename": "oversized_boundary_paths_%s.csv" %
                                str(int(time.time())),
                    "data": data
                }

                self.send_email(recipients, cc, subject, content, report)
