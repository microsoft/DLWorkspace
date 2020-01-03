import logging
import time
import os
import subprocess

from path_tree import PathTree
from path_node import DATETIME_FMT, G, DAY


class StorageManager(object):
    """This class implements a storage manager that scans storages on daily basis.

    Attributes:
        logger: Logging tool.
        config: Configuration for StorageManager.
        execution_interval_days: Number of days in between for consecutive runs.
        last_now: The unix epoch time in seconds.
        scan_points: A list of scan point configurations.
    """
    def __init__(self, config):
        self.logger = logging.getLogger()
        self.config = config
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

    def send_email(self, scan_point):
        pass

    def scan(self):
        """Scans each scan_point and finds overweight and expired nodes."""
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

            tree = PathTree(scan_point)
            tree.walk()

            root = tree.root
            if root is not None:
                self.logger.info("Total number of paths under %s found: %d" %
                                 (tree.path, root.num_subtree_nodes))
            else:
                self.logger.warning("Tree root for path %s is None." % tree.path)

            overweight_nodes = tree.overweight_boundary_nodes
            self.logger.info("Overweight (> %d) boundary paths are:" %
                             tree.overweight_threshold)
            for node in overweight_nodes:
                self.logger.info(node)

            if not "alert_recipients" in scan_point:
                self.logger.info("There is no recipient for %s" % scan_point)
                continue

            subject = "[Storage Alert][%s][%s][Used > %s\%]" % (self.config["cluster_name_friendly"], scan_point["alias"], scan_point["used_percent_threshold"])
            body = "\n".join([node.replace(scan_point["path"], scan_point["alias"])])
            recipients = scan_point["alert_recipients"]
            if not isinstance(recipients, list):
                recipients = recipients.split(",")

            #self.logger.info("")

            #self.logger.info("Expired (access time < %s) boundary paths are:" %
            #                 tree.expiry.strftime(DATETIME_FMT))
            #for node in tree.expired_boundary_nodes:
            #    self.logger.info(node)
            #self.logger.info("")

            #self.logger.info("Emtpy boundary paths are:")
            #for node in tree.empty_boundary_nodes:
            #    self.logger.info(node)
            #self.logger.info("")



            smtp = self.config["smtp"]
            if smtp is None:
                self.logger.warning("stmp is not configured.")
                continue

            message = (
                f"From: {smtp['smtp_from']}\r\n"
                f"To: {';'.join(recipients)}\r\n"
                f"MIME-Version: 1.0\r\n"
                f"Content-type: text/html\r\n"
                f"Subject: {subject}\r\n\r\n{body}"
            )

            try:
                with smtplib.SMTP(smtp["smtp_url"]) as server:
                    server.starttls()
                    server.login(smtp["smtp_auth_username"], smtp['smtp_auth_password'])
                    server.sendmail(smtp["smtp_from"], recepients, message)
                    self.logger.info(f"Email sent to {', '.join(recepients)}")
            except smtplib.SMTPAuthenticationError:
                self.logger.warning('The server didn\'t accept the user\\password combination.')
            except smtplib.SMTPServerDisconnected:
                self.logger.warning('Server unexpectedly disconnected')
            except smtplib.SMTPException as e:
                self.logger.exception('SMTP error occurred: ' + str(e))
