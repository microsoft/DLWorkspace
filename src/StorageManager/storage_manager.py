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
from utils import bytes2human_readable, G, DAY


class StorageManager(object):
    """This class implements a storage manager that scans storages on daily basis.

    Attributes:
        logger: Logging tool.
        config: Configuration for StorageManager.
        execution_interval_days: Number of days in between for consecutive runs.
        last_now: The unix epoch time in seconds.
        scan_points: A list of scan point configurations.
    """
    def __init__(self, config, smtp, cluster_name):
        self.logger = logging.getLogger()
        self.config = config
        self.smtp = smtp
        self.cluster_name = cluster_name

        self.restful_url = self.config.get("restful_url", "http://192.168.255.1:5000")
        self.execution_interval_days = self.config.get("execution_interval_days", 1)
        self.last_now = None
        self.scan_points = self.config.get("scan_points", [])
        assert isinstance(self.scan_points, list)

        self.overweight_threshold = self.config.get("overweight_threshold", 10 * G)
        self.expiry_days = self.config.get("expiry_days", 1)

        self.logger.info("execution_interval_days: %d" %
                         self.config["execution_interval_days"])
        self.logger.info("scan_points: %s" % self.scan_points)

    def run(self):
        """Runs a while loop to monitor scan_points."""
        while True:
            if self.last_now is None:
                self.last_now = time.time()

            try:
                self.scan()
            except Exception as e:
                self.logger.error("StorageManager.scan failed with exception "
                                  "%s" % str(e))

            time2_next_scan = max(0, self.last_now + DAY - time.time())
            self.logger.info("Sleeping for %s sec before next scan." %
                             time2_next_scan)
            time.sleep(time2_next_scan)

            self.last_now = time.time()

    def should_scan(self, scan_point):
        df = subprocess.Popen(["df", scan_point["device_mount"]], stdout=subprocess.PIPE)
        output = df.communicate()[0].decode()
        _, _, _, _, percent, _ = output.split("\n")[1].split()
        return float(percent.strip("%")) > float(scan_point["used_percent_threshold"])

    def send_email(self, sender, recipients, cc, subject, content, report):
        """Send an alert email to recipients

        # https://gist.github.com/BietteMaxime/f75ae41f7b4557274a9f
        """

        # Create message container - the correct MIME type is multipart/mixed to allow attachment.
        full_email = MIMEMultipart("mixed")
        full_email["Subject"] = subject
        full_email["From"] = sender
        full_email["To"] = recipients
        full_email["CC"] = cc

        # Create the body of the message (a plain-text version).
        body = MIMEMultipart("alternative")
        body.attach(MIMEText(content.encode("utf-8"), "plain", _charset="utf-8"))
        full_email.attach(body)

        # Create the attachment of the message in text/csv.
        attachment = MIMENonMultipart('text', 'csv', charset='utf-8')
        attachment.add_header('Content-Disposition', 'attachment', filename=report["filename"])
        cs = Charset('utf-8')
        cs.body_encoding = BASE64
        attachment.set_payload(report["data"].encode('utf-8'), charset=cs)
        full_email.attach(attachment)

        try:
            with smtplib.SMTP(self.smtp["smtp_url"]) as server:
                server.starttls()
                server.login(self.smtp["smtp_auth_username"], self.smtp['smtp_auth_password'])
                server.sendmail(self.smtp["smtp_from"], recipients, full_email.as_string())
                self.logger.info("Successfully sent email to %s" % recipients)
        except smtplib.SMTPAuthenticationError:
            self.logger.warning("The server didn\'t accept the user\\password combination.")
        except smtplib.SMTPServerDisconnected:
            self.logger.warning("Server unexpectedly disconnected")
        except smtplib.SMTPException as e:
            self.logger.exception("SMTP error occurred: " + str(e))

    def get_uid_user(self):
        """Gets UID -> User mapping from restful url"""
        resp = requests.get(self.restful_url + "/GetAllUsers")
        if resp.status_code != 200:
            return {}

        data = json.loads(resp.text)
        uid_user = {}
        for item in data:
            try:
                uid = int(item[1])
                user = item[0]
                uid_user[uid] = user
            except:
                pass
        return uid_user

    def scan(self):
        """Scans each scan_point and finds overweight nodes. Sends alert."""
        uid_user = self.get_uid_user()

        for scan_point in self.scan_points:
            if "device_mount" not in scan_point:
                self.logger.warning("device_mount does not exist in %s. "
                                    "continue." % scan_point)
                continue

            if "used_percent_threshold" not in scan_point:
                self.logger.warning("used_percent_threshold does not exist in "
                                    "%s. continue." % scan_point)
                continue

            if "path" not in scan_point:
                self.logger.warning("path does not exist in %s. continue." %
                                    scan_point)
                continue

            if not self.should_scan(scan_point):
                self.logger.info("%s used percent is smaller than threshold. "
                                 "continue." % scan_point)
                continue

            if "overweight_threshold" not in scan_point:
                self.logger.info("overweight_threshold does not exist in "
                                 "%s. Using parent overweight_threshold %d." %
                                 (scan_point, self.overweight_threshold))
                scan_point["overweight_threshold"] = self.overweight_threshold

            if "expiry_days" not in scan_point:
                self.logger.info("expiry_days does not exist in %s. "
                                 "Using parent expiry_days %d." %
                                 (scan_point, self.expiry_days))
                scan_point["expiry_days"] = self.expiry_days

            if not os.path.exists(scan_point["path"]):
                self.logger.warning("%s does not exist in file system. "
                                    "continue." % scan_point)
                continue

            scan_point["now"] = self.last_now

            self.logger.info("Scanning scan_point %s" % scan_point)

            tree = PathTree(scan_point, uid_user=uid_user)
            tree.walk()

            root = tree.root
            if root is not None:
                self.logger.info("Total number of paths under %s found: %d" %
                                 (tree.path, root.num_subtree_nodes))
            else:
                self.logger.warning("Tree root for path %s is None." % tree.path)

            overweight_nodes = tree.overweight_boundary_nodes

            if self.smtp is None:
                self.logger.warning("stmp is not configured.")
                continue

            sender = self.smtp["smtp_from"]

            # Group overweight nodes by user
            user_overweight_nodes = {}
            default_recipient = scan_point.get("default_recipients", None)
            for node in overweight_nodes:
                owner = node.owner
                if owner == "" and default_recipient is None:
                    continue
                elif owner == "" and default_recipient is not None:
                    owner = default_recipient

                if owner not in user_overweight_nodes:
                    user_overweight_nodes[owner] = []
                user_overweight_nodes[owner].append(node)

            for recipient, nodes in user_overweight_nodes.items():
                self.logger.info("Overweight (> %d) boundary paths for %s are:" %
                                 (tree.overweight_threshold, recipient))
                for node in nodes:
                    self.logger.info(node)

                cc = self.smtp["cc"]

                subject = "%s: %s usage > %s%% - %s" % \
                          (self.cluster_name,
                           scan_point["alias"],
                           scan_point["used_percent_threshold"],
                           recipient)

                content = "%s storage mountpoint %s usage is > %s%%. " \
                          "Full list of your oversized boundary paths (> %s) is in the attached CSV. " \
                          "Please help reduce the size.\n\n" % \
                          (self.cluster_name,
                           scan_point["alias"],
                           scan_point["used_percent_threshold"],
                           bytes2human_readable(self.overweight_threshold))

                header = "size_in_bytes,owner,path\n"

                preview_len = min(20, len(nodes))
                content += header
                for node in nodes[0:preview_len]:
                    content += "%s,%s,%s\n" % (node.size, node.owner,
                                               node.path.replace(scan_point["path"],
                                                                 scan_point["alias"],
                                                                 1))

                data = header
                for node in nodes:
                    cur_node = "%s,%s,%s\n" % (node.size, node.owner,
                                               node.path.replace(scan_point["path"],
                                                                 scan_point["alias"],
                                                                 1))
                    data += cur_node

                report = {
                    "filename": "oversized_boundary_paths %s.csv" % str(int(time.time())),
                    "data": data
                }

                self.send_email(sender, recipient, cc, subject, content, report)
