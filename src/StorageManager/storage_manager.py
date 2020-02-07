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
from datetime import datetime
from utils import bytes2human_readable, G


ENCODING = "utf-8"
MAX_NODES_IN_REPORT = 5000
DEFAULT_REGEX_WHITELIST = {
    "/data/share/work": [
        r"^/data/share/work/[0-9a-zA-Z\-]+$",
        r"^/data/share/work/[0-9a-zA-Z\-]+/\..*"
    ]
}


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
        self.days_to_delete_after_expiry = \
            self.config.get("days_to_delete_after_expiry", None)

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

    def send_email(self, recipients, cc, subject, content, reports):
        """Sends an email with attachment.
        Refer to https://gist.github.com/BietteMaxime/f75ae41f7b4557274a9f

        Args:
            recipients: To whom to send the email.
            cc: To whom to cc the email.
            subject: Email subject.
            content: Email body content
            reports: List of dictionaries containing "filename", "data" to
                construct CSV attachments.

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
        for report in reports:
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

    def get_uid_to_user(self):
        """Gets uid -> user mapping from restful url"""
        query_url = self.restful_url + "/GetAllUsers"
        resp = requests.get(query_url)
        if resp.status_code != 200:
            self.logger.warning("Querying %s failed.", query_url)
            return {}

        data = json.loads(resp.text)
        uid_to_user = {}
        for item in data:
            try:
                uid = int(item[1])
                user = item[0]
                uid_to_user[uid] = user
            except Exception as e:
                self.logger.warning("Parsing %s failed: %s", item, e)
        return uid_to_user

    def group_nodes_by_owner(self, nodes):
        nodes_by_owner = {}
        default_recipient = self.smtp.get("default_recipients", None)
        self.logger.info("default recipient is %s", default_recipient)

        for node in nodes:
            owner = node.owner
            if owner == "" and default_recipient is None:
                continue
            elif owner == "" and default_recipient is not None:
                owner = default_recipient

            if owner not in nodes_by_owner:
                nodes_by_owner[owner] = []
            nodes_by_owner[owner].append(node)

        return nodes_by_owner

    def assemble_node_list_by_owner(self,
                                    overweight_nodes_by_owner,
                                    expired_nodes_by_owner,
                                    empty_nodes_by_owner):
        node_list_by_owner = {}
        overweight_owners = set(overweight_nodes_by_owner.keys())
        expired_owners = set(expired_nodes_by_owner.keys())
        empty_owners = set(empty_nodes_by_owner.keys())
        all_owners = overweight_owners.union(expired_owners).union(empty_owners)

        for owner in all_owners:
            node_list_by_owner[owner] = {
                "overweight": overweight_nodes_by_owner.get(owner, []),
                "expired": expired_nodes_by_owner.get(owner, []),
                "empty": empty_nodes_by_owner.get(owner, []),
            }

        return node_list_by_owner

    def generate_report(self, nodes, scan_point, node_type, preview_len=20):
        # Log all nodes
        for node in nodes:
            self.logger.info(node)

        path = scan_point["path"]
        alias = scan_point["alias"]

        header = "last_access_time,size_in_bytes,readable_size,owner,path\n"

        preview_len = min(preview_len, len(nodes))
        preview = header
        for node in nodes[0:preview_len]:
            preview += "%s,%s,%s,%s,%s\n" % (
                node.subtree_atime,
                node.subtree_size,
                bytes2human_readable(node.subtree_size),
                node.owner,
                node.path.replace(path, alias, 1))
        if preview_len < len(nodes):
            preview += "...\n"

        data = header
        max_len = min(MAX_NODES_IN_REPORT, len(nodes))
        for node in nodes[0:max_len]:
            cur_node = "%s,%s,%s,%s,%s\n" % (
                node.subtree_atime,
                node.subtree_size,
                bytes2human_readable(node.subtree_size),
                node.owner,
                node.path.replace(path, alias, 1))
            data += cur_node

        report = {
            "filename": "%s_boundary_paths_%s.csv" % (
                node_type, datetime.fromtimestamp(int(time.time()))),
            "data": data
        }

        return preview, report

    def send_email_to_owners(self, node_list_by_owner, scan_point):
        alias = scan_point["alias"]
        used_percent = scan_point["used_percent"]
        used_percent_alert_threshold = \
            scan_point["used_percent_alert_threshold"]
        overweight_threshold = scan_point["overweight_threshold"]
        expiry_days = scan_point["expiry_days"]
        days_to_delete_after_expiry = scan_point["days_to_delete_after_expiry"]

        for owner, nodes_info in node_list_by_owner.items():
            overweight_nodes = nodes_info["overweight"]
            expired_nodes = nodes_info["expired"]
            empty_nodes = nodes_info["empty"]

            self.logger.info("Generating overweight report for owner %s", owner)
            overweight_preview, overweight_report = \
                self.generate_report(overweight_nodes, scan_point, "overweight")
            self.logger.info("Generating expired report for owner %s", owner)
            expired_preview, expired_report = \
                self.generate_report(expired_nodes, scan_point, "expired")
            self.logger.info("Generating empty report for owner %s", owner)
            empty_preview, empty_report = \
                self.generate_report(empty_nodes, scan_point, "empty")

            reports = [
                overweight_report,
                expired_report,
                empty_report,
            ]

            recipients = owner.split(",")
            cc = self.smtp["cc"].split(",")

            subject = "[%s]" % self.cluster_name
            if "vc" in scan_point:
                subject += "[%s]" % scan_point["vc"]

            subject += "[Storage Manager][%s] Storage usage of %s is at " \
                       "%s%% > %s%%" % \
                       (owner.split("@")[0],
                        alias,
                        used_percent,
                        used_percent_alert_threshold)

            content = "%s storage mountpoint %s usage is at %s%% > %s%%.\n" % \
                      (self.cluster_name,
                       alias,
                       used_percent,
                       used_percent_alert_threshold)

            # Content for overweight nodes
            content += "\nPlease help reduce the size of your over-sized " \
                       "boundary paths (> %s) in the attached report %s. The " \
                       "report only contains up to %s paths\n" % \
                       (bytes2human_readable(overweight_threshold),
                        overweight_report["filename"],
                        MAX_NODES_IN_REPORT)
            content += overweight_preview

            # Content for expired nodes
            content += "\nPlease remove/use the expired boundary paths (last " \
                       "access time older than %s days ago) in the attached " \
                       "report %s. The report only contains up to %s paths." \
                       "\n" % \
                       (expiry_days,
                        expired_report["filename"],
                        MAX_NODES_IN_REPORT)
            if days_to_delete_after_expiry is not None:
                content += "They are automatically deleted if their last " \
                           "access time are older than %s days ago.\n" % \
                           (int(expiry_days) + int(days_to_delete_after_expiry))
            content += expired_preview

            # Content for empty nodes
            content += "\nPlease consider removing your empty directories in " \
                       "the attached report %s. The report only contains up " \
                       "to %s paths.\n" % \
                       (empty_report["filename"],
                        MAX_NODES_IN_REPORT)
            content += empty_preview

            self.send_email(recipients, cc, subject, content, reports)

    def scan_point_is_valid(self, scan_point):
        """scan_point is mutated"""
        # device_mount, used_percent_alert_threshold, path must exist
        if "device_mount" not in scan_point:
            self.logger.warning("device_mount missing in %s. Skip.", scan_point)
            return False
        device_mount = scan_point["device_mount"]

        if "path" not in scan_point:
            self.logger.warning("path missing in %s. Skip.", scan_point)
            return False

        if "alias" not in scan_point:
            scan_point["alias"] = scan_point["path"]

        if "used_percent_alert_threshold" not in scan_point:
            self.logger.warning("user_percent_alert_threshold missing in "
                                "%s. Setting to 90.", scan_point)
            scan_point["used_percent_alert_threshold"] = 90
        used_percent_alert_threshold = \
            float(scan_point["used_percent_alert_threshold"])

        # Only scan if alert threshold is reached
        used_percent = self.scan_point_used_percent(device_mount)
        scan_point["used_percent"] = used_percent
        if used_percent is None:
            self.logger.warning("used_percent is None. Skip.")
            return False

        if used_percent < used_percent_alert_threshold:
            self.logger.info("%s used percent %s < threshold %s. Skip.",
                             scan_point,
                             used_percent,
                             used_percent_alert_threshold)
            return False

        if "overweight_threshold" not in scan_point:
            self.logger.info("overweight_threshold does not exist in %s. "
                             "Using parent overweight_threshold %d.",
                             scan_point, self.overweight_threshold)
            scan_point["overweight_threshold"] = self.overweight_threshold

        if "expiry_days" not in scan_point:
            self.logger.info("expiry_days does not exist in %s. "
                             "Using parent expiry_days %d.",
                             scan_point, self.expiry_days)
            scan_point["expiry_days"] = self.expiry_days

        if "days_to_delete_after_expiry" not in scan_point:
            self.logger.info("days_to_delete_after_expiry does not exist in "
                             "%s. Using parent days_to_delete_after_expiry %s",
                             scan_point, self.days_to_delete_after_expiry)
            scan_point["days_to_delete_after_expiry"] = \
                self.days_to_delete_after_expiry

        if not os.path.exists(scan_point["path"]):
            self.logger.warning("%s is absent in file system. Skip.",
                                scan_point)
            return False

        scan_point["now"] = self.last_now

        if scan_point["path"] in DEFAULT_REGEX_WHITELIST:
            default_regex = DEFAULT_REGEX_WHITELIST[scan_point["path"]]
            if "regex_whitelist" not in scan_point:
                scan_point["regex_whitelist"] = []
            scan_point["regex_whitelist"].extend(default_regex)

        return True

    def process_emails_for_tree(self, tree, scan_point):
        # Get overweight, expired, and empty nodes
        overweight_nodes = tree.overweight_boundary_nodes
        expired_nodes = tree.expired_boundary_nodes
        empty_nodes = tree.empty_boundary_nodes

        # Group nodes by owner
        overweight_nodes_by_owner = \
            self.group_nodes_by_owner(overweight_nodes)
        expired_nodes_by_owner = self.group_nodes_by_owner(expired_nodes)
        empty_nodes_by_owner = self.group_nodes_by_owner(empty_nodes)

        # Assemble node list by owner
        node_list_by_owner = self.assemble_node_list_by_owner(
            overweight_nodes_by_owner,
            expired_nodes_by_owner,
            empty_nodes_by_owner
        )

        # Send emails to owners
        self.send_email_to_owners(node_list_by_owner, scan_point)

    def delete_expired_nodes(self, tree):
        if len(tree.expired_boundary_nodes_to_delete) == 0:
            self.logger.info("No expired nodes to delete.")
            return

        self.logger.info("Deleting expired nodes ...")
        for node in tree.expired_boundary_nodes_to_delete:
            if os.path.exists(node.path):
                if node.isdir:
                    os.rmdir(node.path)
                else:
                    os.remove(node.path)
            else:
                self.logger.warning("%s does not exist")

    def scan_a_scan_point(self, scan_point, uid_to_user=None):
        if not self.scan_point_is_valid(scan_point):
            return

        self.logger.info("Scanning scan point %s", scan_point)

        tree = PathTree(scan_point, uid_to_user=uid_to_user)
        tree.walk()
        tree.filter()

        root = tree.root
        if root is not None:
            self.logger.info("Total number of paths under %s found: %d",
                             tree.path, root.num_subtree_nodes)
        else:
            self.logger.warning("Tree root for %s is None.", tree.path)

        if self.smtp is None:
            self.logger.warning("stmp is not configured. Skip email.")
        else:
            self.process_emails_for_tree(tree, scan_point)

        self.delete_expired_nodes(tree)

    def scan(self):
        """Scans each scan_point and finds overweight nodes. Sends alert."""
        uid_to_user = self.get_uid_to_user()

        for sp in self.scan_points:
            self.logger.info("Scanning scan_point: %s", sp)
            self.scan_a_scan_point(sp, uid_to_user=uid_to_user)
