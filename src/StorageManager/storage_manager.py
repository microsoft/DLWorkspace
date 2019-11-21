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
        self.execution_interval_days = self.config["execution_interval_days"]
        self.last_now = None
        self.scan_points = self.config["scan_points"]
        assert isinstance(self.scan_points, list)

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
        tree = None
        for scan_point in self.scan_points:
            if "path" not in scan_point:
                self.logger.warning("path does not exist in %s. continue." %
                                    scan_point)
                continue

            if "overweight_threshold" not in scan_point:
                self.logger.warning("overweight_threshold does not exist in "
                                    "%s. continue" % scan_point)
                continue

            if "expiry_days" not in scan_point:
                self.logger.warning("expiry_days does not exist in %s. "
                                    "continue." % scan_point)
                continue

            if not os.path.exists(scan_point["path"]):
                self.logger.warning("%s does not exist in file system. "
                                    "continue." % scan_point)
                continue

            scan_point["now"] = self.last_now

            self.logger.info("Scanning scan_point %s" % scan_point)

            del tree
            tree = PathTree(scan_point)
            tree.create()

            root = tree.root
            self.logger.info("Total number of paths found: %d" %
                             root.num_subtree_nodes)

            overweight_nodes = tree.find_overweight_nodes()
            self.logger.info("Overweight (> %d) paths are:" %
                             tree.overweight_threshold)
            for node in overweight_nodes:
                self.logger.info(node)

            expired_nodes = tree.find_expired_nodes()
            self.logger.info("Expired (access time < %s) paths are:" %
                             tree.expiry.strftime(DATETIME_FMT))
            for node in expired_nodes:
                self.logger.info(node)
