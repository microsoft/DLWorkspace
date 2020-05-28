#!/usr/bin/env python3

import logging
import logging.config
import time
import os

from prometheus_client import Histogram
from prometheus_client.core import GaugeMetricFamily
from path_tree import PathTree
from rule import OverweightRule, ExpiredRule, ExpiredToDeleteRule, EmptyRule
from utils import G, df, get_uid_to_user, keep_ancestor_paths

logger = logging.getLogger(__name__)


class StorageManager(object):
    """This class implements a storage manager that scans defined scan_points
     on regular basis.

    Attributes:
        config: Configuration for StorageManager.
        execution_interval: Number of seconds between applying rules.
        last_now: The unix epoch time in seconds.
        scan_points: A list of scan point configurations.
        overweight_threshold: The threshold for deciding an overweight path
            node.
        expiry_days: Number of days to expire.
        days_to_delete_after_expiry: Days to delete after expiration.
    """
    def __init__(self, config, smtp, cluster_name, atomic_ref):
        self.config = config
        self.smtp = smtp
        self.cluster_name = cluster_name
        self.atomic_ref = atomic_ref

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

        # Prefix with host-fs since storage mounts can use any path on host
        for sp in self.scan_points:
            sp["path"] = os.path.join("/host-fs", sp["path"].lstrip("/"))

        self.last_now = time.time()
        first_time = True

        while True:
            try:
                # Scan all scan points to collect storage information
                self.scan()

                # Generate usage info
                self.gen_usage_by_user_from_trees()

                # Apply rules and send alert emails when time is up.
                if not first_time and \
                        self.last_now + self.execution_interval > time.time():
                    logger.info("Time is not up for applying rules.")
                else:
                    if first_time:
                        first_time = False
                    logger.info("Applying rules ...")
                    self.apply_rules()
                    self.last_now = time.time()
            except Exception as e:
                logger.exception("StorageManager.run failed")

    def scan(self):
        """Scans each scan_point. Sends alert when time is up."""
        uid_to_user = get_uid_to_user(self.restful_url)
        for scan_point in self.scan_points:
            self.scan_a_point(scan_point, uid_to_user=uid_to_user)

    def gen_usage_by_user_from_trees(self):
        """Generate usage by user from all trees in scan points for scraping"""
        ancestors = keep_ancestor_paths([
            sp.get("path") for sp in self.scan_points
            if sp.get("path") is not None])

        usage_gauge = GaugeMetricFamily("storage_usage_in_bytes_by_user",
                                        "storage usage by each user",
                                        labels=["vc", "mountpoint", "user"])
        for sp in self.scan_points:
            if sp.get("path") not in ancestors:
                continue

            vc = sp.get("vc") or "cluster"
            mountpoint = sp.get("alias") or "N/A"
            tree = sp.get("tree")
            if tree is None:
                continue

            for user, usage in tree.usage_by_user.items():
                usage_gauge.add_metric([vc, mountpoint, user], usage)

        self.atomic_ref.set(usage_gauge)

    def apply_rules(self):
        """Only apply rules when time is up"""
        for scan_point in self.scan_points:
            tree = scan_point.get("tree")
            if tree is None:
                logger.warning(
                    "cannot apply rules to scan point %s for None tree.",
                    scan_point)
                continue

            OverweightRule(scan_point, tree.overweight_boundary_nodes).process()
            ExpiredRule(scan_point, tree.expired_boundary_nodes).process()
            ExpiredToDeleteRule(
                scan_point, tree.expired_boundary_nodes_to_delete).process()
            EmptyRule(scan_point, tree.empty_boundary_nodes).process()

    def scan_a_point(self, scan_point, uid_to_user=None):
        if not self.valid_scan_point(scan_point):
            return

        logger.info("Scanning scan point %s", scan_point)

        tree = PathTree(scan_point, uid_to_user=uid_to_user)
        tree.walk()
        scan_point["tree"] = tree

        # Log some info
        root = tree.root
        if root is not None:
            logger.info("Total number of paths under %s found: %d",
                        tree.path, root.num_subtree_nodes)
        else:
            logger.warning("Tree root for %s is None.", tree.path)
            return

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

        # Check used percent
        used_percent = df(scan_point["path"])
        scan_point["used_percent"] = used_percent
        if used_percent is None:
            logger.warning("used_percent cannot be retrieved.")
        else:
            logger.info("%s used percent is %s", scan_point["path"], 
                        used_percent)

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
