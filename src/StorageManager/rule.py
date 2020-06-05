#!/usr/bin/env python3

import logging
import logging.config
import time

from datetime import datetime
from utils import override, \
    send_email, \
    bytes2human_readable, \
    post_order_delete, \
    MAX_NODES_IN_REPORT

logger = logging.getLogger(__name__)


class Rule(object):
    def __init__(self, config, nodes, name=None):
        """Base class Rule constructor.

        Args:
            config: A dictionary containing properties.
            name: Name for the rule.
            nodes: A node list
        """
        self.config = config
        self.smtp = config.get("smtp", None)
        self.cluster_name = config.get("cluster_name", None)
        self.enabled = True
        self.name = name
        self.path = config["path"]
        self.alias = config.get("alias", self.path)
        self.vc = config.get("vc", None)
        self.nodes = nodes
        self.nodes_by_owner = {}

    def process(self):
        # Client should call this method
        if not self.enabled:
            logger.warning("Rule %s is NOT enabled for %s", self.name,
                           self.path)
            return

        logger.info("Rule %s is enabled for %s. Processing ...", self.name,
                    self.path)
        self.run_rule()

    @override
    def run_rule(self):
        self.group_nodes_by_owner()

    @override
    def generate_subject(self, owner, nodes, preview, report):
        # To override in subclass
        return ""

    @override
    def generate_content(self, owner, nodes, preview, report):
        # To override in subclass
        content = ""
        content += preview
        return content

    def group_nodes_by_owner(self):
        nodes_by_owner = {}
        default_owner = self.smtp.get("default_recipients", None)

        for node in self.nodes:
            owner = node.owner
            if owner == "" and default_owner is None:
                continue
            elif owner == "" and default_owner is not None:
                owner = default_owner

            if owner not in nodes_by_owner:
                nodes_by_owner[owner] = []
            nodes_by_owner[owner].append(node)

        self.nodes_by_owner = nodes_by_owner

    def send_emails_to_owners(self):
        for owner, nodes in self.nodes_by_owner.items():
            self.send_email_to_owner(owner, nodes)

    def send_email_to_owner(self, owner, nodes):
        preview, report = self.generate_report(owner, nodes)
        recipients = owner.split(",")
        cc = self.smtp["cc"].split(",")
        subject = self.generate_subject(owner, nodes, preview, report)
        content = self.generate_content(owner, nodes, preview, report)
        send_email(self.smtp, recipients, cc, subject, content, [report])

    def generate_report(self, owner, nodes, preview_len=20):
        logger.info("Generating %s report for owner %s under %s", self.name,
                    owner, self.path)
        # Log all nodes
        for node in nodes:
            logger.info(node)

        path = self.config["path"]
        alias = self.config["alias"]

        header = "atime,mtime,time,size_in_bytes,readable_size,owner,path\n"

        preview_len = min(preview_len, len(nodes))
        preview = header
        for node in nodes[0:preview_len]:
            preview += "%s,%s,%s,%s,%s,%s,%s\n" % (
                node.subtree_atime, node.subtree_mtime, node.subtree_time,
                node.subtree_size, bytes2human_readable(node.subtree_size),
                node.owner, node.path.replace(path, alias, 1))
        if preview_len < len(nodes):
            preview += "...\n"

        data = header
        max_len = min(MAX_NODES_IN_REPORT, len(nodes))
        for node in nodes[0:max_len]:
            cur_node = "%s,%s,%s,%s,%s,%s,%s\n" % (
                node.subtree_atime, node.subtree_mtime, node.subtree_time,
                node.subtree_size, bytes2human_readable(node.subtree_size),
                node.owner, node.path.replace(path, alias, 1))
            data += cur_node

        report = {
            "filename":
                "%s_boundary_paths_%s.csv" %
                (self.name, datetime.fromtimestamp(int(time.time()))),
            "data":
                data
        }

        return preview, report

    def delete_nodes(self):
        if len(self.nodes) == 0:
            logger.info("No nodes to delete for rule %s.", self.name)
            return

        logger.info("Deleting nodes for rule %s...", self.name)
        for node in self.nodes:
            if "*" in node.path:
                logger.warning(
                    "Skip path %s containing wildcard '*' to "
                    "prevent mass deleting", node.path)
                continue
            try:
                # Delete files with a slight nap in between to avoid locking
                # the file system
                post_order_delete(node.path, nap=0.01)
            except:
                logger.exception("Exception in deleting path %s.",
                                 node.path,
                                 exc_info=True)


class OverweightRule(Rule):
    def __init__(self, config, nodes):
        super(OverweightRule, self).__init__(config, nodes, name="overweight")

        self.enabled = config.get("overweight_rule", True)
        self.used_percent = config["used_percent"]
        self.used_percent_alert_threshold = \
            config["used_percent_alert_threshold"]
        self.overweight_threshold = config["overweight_threshold"]

        if self.used_percent < self.used_percent_alert_threshold:
            logger.info("Usage %s%% < threshold %s%%. Disable rule %s.",
                        self.used_percent, self.used_percent_alert_threshold,
                        self.name)
            self.enabled = False

    def run_rule(self):
        super(OverweightRule, self).run_rule()
        self.send_emails_to_owners()

    def generate_subject(self, owner, nodes, preview, report):
        subject = "[%s]" % self.cluster_name
        subject += "[%s]" % self.vc if self.vc is not None else ""
        subject += "[Storage Manager][%s] Storage usage of %s is at " \
                   "%s%% >= %s%%" % \
                   (owner.split("@")[0],
                    self.alias,
                    self.used_percent,
                    self.used_percent_alert_threshold)

        return subject

    def generate_content(self, owner, nodes, preview, report):
        content = "%s storage mountpoint %s usage is at %s%% >= %s%%.\n" % \
                  (self.cluster_name,
                   self.alias,
                   self.used_percent,
                   self.used_percent_alert_threshold)

        # Content for overweight nodes
        content += "\nPlease help reduce the size of your over-sized " \
                   "boundary paths (> %s) in the attached report \"%s\". The " \
                   "report only contains up to %s paths\n" % \
                   (bytes2human_readable(self.overweight_threshold),
                    report["filename"],
                    MAX_NODES_IN_REPORT)
        content += preview
        return content


class ExpiredRule(Rule):
    def __init__(self, config, nodes):
        super(ExpiredRule, self).__init__(config, nodes, name="expired")

        self.enabled = config.get("expired_rule", False)
        self.expiry_days = self.config.get("expiry_days", 31)
        self.days_to_delete_after_expiry = \
            self.config.get("days_to_delete_after_expiry", None)

    def run_rule(self):
        super(ExpiredRule, self).run_rule()
        self.send_emails_to_owners()

    def generate_subject(self, owner, nodes, preview, report):
        subject = "[%s]" % self.cluster_name
        subject += "[%s]" % self.vc if self.vc is not None else ""
        subject += "[Storage Manager][%s] Expired paths detected at %s" % \
                   (owner.split("@")[0], self.alias)

        return subject

    def generate_content(self, owner, nodes, preview, report):
        content = "\nPlease remove/use the expired boundary paths (last " \
                  "access time older than %s days ago) in the attached " \
                  "report \"%s\". The report only contains up to %s paths." \
                  "\n" % \
                  (self.expiry_days,
                   report["filename"],
                   MAX_NODES_IN_REPORT)
        if self.days_to_delete_after_expiry is not None:
            content += "They are automatically deleted if their last " \
                       "access time are older than %s days ago.\n" % \
                       (int(self.expiry_days) +
                        int(self.days_to_delete_after_expiry))
        content += preview

        return content


class ExpiredToDeleteRule(Rule):
    def __init__(self, config, nodes):
        super(ExpiredToDeleteRule, self).__init__(config,
                                                  nodes,
                                                  name="expired_to_delete")

        self.enabled = config.get("expired_to_delete_rule", False)
        expiry_days = self.config.get("expiry_days", 31)
        days_to_delete_after_expiry = \
            self.config.get("days_to_delete_after_expiry", None)
        logger.info("expiry_days is %s. days_to_delete_after_expiry is %s",
                    expiry_days, days_to_delete_after_expiry)

    def run_rule(self):
        super(ExpiredToDeleteRule, self).run_rule()
        self.delete_nodes()


class EmptyRule(Rule):
    def __init__(self, config, nodes):
        super(EmptyRule, self).__init__(config, nodes, name="empty")

        self.enabled = config.get("empty_rule", False)

    def run_rule(self):
        super(EmptyRule, self).run_rule()
        self.send_emails_to_owners()

    def generate_subject(self, owner, nodes, preview, report):
        subject = "[%s]" % self.cluster_name
        subject += "[%s]" % self.vc if self.vc is not None else ""
        subject += "[Storage Manager][%s] Empty paths detected at %s" % \
                   (owner.split("@")[0], self.alias)

        return subject

    def generate_content(self, owner, nodes, preview, report):
        content = "\nPlease consider removing the empty boundary paths in " \
                  "the attached report \"%s\". The report only contains " \
                  "up to %s paths. \n" % \
                  (report["filename"],
                   MAX_NODES_IN_REPORT)
        content += preview

        return content
