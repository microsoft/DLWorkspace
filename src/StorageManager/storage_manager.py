#!/usr/bin/env python3

import logging
import logging.config
import time
import os

from path_tree import PathTree
from rule import OverweightRule, ExpiredRule, ExpiredToDeleteRule, EmptyRule
from utils import G, df, get_uid_to_user

logger = logging.getLogger(__name__)


class StorageManager(object):
    """This class implements a storage manager that scans defined scan_points
     on regular basis.

    Attributes:
        logger: Logging tool.
        config: Configuration for StorageManager.
        execution_interval: Number of seconds in between for consecutive runs.
        last_now: The unix epoch time in seconds.
        scan_points: A list of scan point configurations.
        overweight_threshold: The threshold for deciding an overweight path
            node.
        expiry_days: Number of days to expire.
        days_to_delete_after_expiry: Days to delete after expiration.
    """
    def __init__(self, config, smtp, cluster_name):
        self.config = config
        self.smtp = smtp
        self.cluster_name = cluster_name

        default_restful_url = "http://192.168.255.1:5000"
        self.restful_url = self.config.get("restful_url", default_restful_url)

        self.execution_interval = self.config.get("execution_interval", 86400)
        self.last_now = None
        self.scan_points = self.config.get("scan_points", [])
        assert isinstance(self.scan_points, list)

        # For identifying large paths
        self.overweight_threshold = self.config.get("overweight_threshold",
                                                    200 * G)
        # For identifying expired paths
        self.expiry_days = self.config.get("expiry_days", 31)
        self.days_to_delete_after_expiry = \
            self.config.get("days_to_delete_after_expiry", None)

        logger.info("config: %s", self.config)
        logger.info("smtp: %s", self.smtp)
        logger.info("cluster_name: %s", self.cluster_name)

    def run(self):
        """Runs a while loop to monitor scan_points."""
        while True:
            if self.last_now is None:
                self.last_now = time.time()

            try:
                self.scan()
            except Exception as e:
                logger.error("scan failed with exception %s", e)

            next_scan_time = self.last_now + self.execution_interval
            time2_next_scan = max(0, next_scan_time - time.time())
            logger.info("Sleeping for %s sec before next scan.",
                        time2_next_scan)
            time.sleep(time2_next_scan)

            self.last_now = time.time()

    def scan(self):
        """Scans each scan_point. Sends alert."""
        uid_to_user = get_uid_to_user(self.restful_url)
        for scan_point in self.scan_points:
            logger.info("Scanning scan_point: %s", scan_point)
            self.scan_a_point(scan_point, uid_to_user=uid_to_user)

    def scan_a_point(self, scan_point, uid_to_user=None):
        if not self.valid_scan_point(scan_point):
            return

        logger.info("Scanning scan point %s", scan_point)

        tree = PathTree(scan_point, uid_to_user=uid_to_user)
        tree.walk()

        root = tree.root
        if root is not None:
            logger.info("Total number of paths under %s found: %d",
                        tree.path,
                        root.num_subtree_nodes)
        else:
            logger.warning("Tree root for %s is None.", tree.path)
            return

        self.process_tree(tree, scan_point)

    def valid_scan_point(self, scan_point):
        """scan_point is mutated"""
        if "path" not in scan_point:
            logger.warning("path missing in %s. Skip.", scan_point)
            return False

        if not os.path.exists(scan_point["path"]):
            logger.warning("%s is absent in file system. Skip.", scan_point)
            return False

        if "alias" not in scan_point:
            scan_point["alias"] = scan_point["path"]

        if "used_percent_alert_threshold" not in scan_point:
            logger.warning("user_percent_alert_threshold missing in "
                           "%s. Setting to 90.", scan_point)
            scan_point["used_percent_alert_threshold"] = 90
        scan_point["used_percent_alert_threshold"] = \
            float(scan_point["used_percent_alert_threshold"])

        # Only scan if alert threshold is reached
        used_percent = df(scan_point["path"])
        scan_point["used_percent"] = used_percent
        if used_percent is None:
            logger.warning("used_percent is None. Skip.")
            return False
        else:
            logger.info("%s used percent is %s", scan_point, used_percent)

        if "overweight_threshold" not in scan_point:
            logger.info("overweight_threshold does not exist in %s. "
                        "Using parent overweight_threshold %d.",
                        scan_point, self.overweight_threshold)
            scan_point["overweight_threshold"] = self.overweight_threshold

        if "expiry_days" not in scan_point:
            logger.info("expiry_days does not exist in %s. "
                        "Using parent expiry_days %d.",
                        scan_point, self.expiry_days)
            scan_point["expiry_days"] = self.expiry_days

        if "days_to_delete_after_expiry" not in scan_point:
            logger.info("days_to_delete_after_expiry does not exist in "
                        "%s. Using parent days_to_delete_after_expiry %s",
                        scan_point, self.days_to_delete_after_expiry)
            scan_point["days_to_delete_after_expiry"] = \
                self.days_to_delete_after_expiry

        scan_point["now"] = self.last_now

        scan_point["smtp"] = self.smtp
        scan_point["cluster_name"] = self.cluster_name

        return True

    def process_tree(self, tree, scan_point):
        c = scan_point
        OverweightRule(c, tree.overweight_boundary_nodes).process()
        ExpiredRule(c, tree.expired_boundary_nodes).process()
        ExpiredToDeleteRule(c, tree.expired_boundary_nodes_to_delete).process()
        EmptyRule(c, tree.empty_boundary_nodes).process()

