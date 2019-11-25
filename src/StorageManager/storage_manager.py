import logging
import time
import os

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

    def scan(self):
        """Scans each scan_point and finds overweight and expired nodes."""
        for scan_point in self.scan_points:
            if "path" not in scan_point:
                self.logger.warning("path does not exist in %s. continue." %
                                    scan_point)
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
            self.logger.info("")

            self.logger.info("Expired (access time < %s) boundary paths are:" %
                             tree.expiry.strftime(DATETIME_FMT))
            for node in tree.expired_boundary_nodes:
                self.logger.info(node)
            self.logger.info("")

            self.logger.info("Emtpy boundary paths are:")
            for node in tree.empty_boundary_nodes:
                self.logger.info(node)
            self.logger.info("")
