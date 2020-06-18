#!/usr/bin/env python3

import argparse
import datetime
import logging
import os
import requests
import time
import urllib.parse
import yaml

from logging import handlers
from requests.exceptions import ConnectionError
from constant import REPAIR_STATE, \
    REPAIR_STATE_LAST_UPDATE_TIME, \
    REPAIR_UNHEALTHY_RULES
from util import State, K8sUtil, RestUtil
from util import register_stack_trace_dump, get_logging_level, parse_for_nodes
from rule import instantiate_rules

logger = logging.getLogger(__name__)


class RepairManager(object):
    """RepairManager controls the logic of repair cycle of each worker node.
    """
    def __init__(self, rules, config, agent_port, k8s_util, rest_util, interval=30,
                 dry_run=False):
        self.rules = rules
        self.config = config
        self.agent_port = agent_port
        self.dry_run = dry_run

        self.k8s_util = k8s_util
        self.rest_util = rest_util
        self.interval = interval

        self.nodes = []

    def get_repair_state(self):
        """Refresh nodes based on new info from kubernetes and DB. Refresh
        metrics data in rules Prometheus.
        """
        try:
            k8s_nodes = self.k8s_util.list_node()
            k8s_pods = self.k8s_util.list_pods()
            vc_list = self.rest_util.list_vcs().get("result", {})
            self.nodes = parse_for_nodes(
                k8s_nodes, k8s_pods, vc_list, self.rules, self.config)
            [rule.update_data() for rule in self.rules]
        except:
            logger.exception("failed to get repair state")
            self.nodes = []

    def run(self):
        # Main loop for repair cycle of nodes.
        while True:
            try:
                self.get_repair_state()
                logger.info(
                    "Running repair update on %s nodes against rules: %s",
                    len(self.nodes),
                    [rule.__class__.__name__ for rule in self.rules])
                for node in self.nodes:
                    if self.validate(node):
                        state = node.state
                        self.update(node)
                        if node.state != state:
                            logger.info(
                                "node %s (%s) repair state: %s -> %s. "
                                "unhealthy rules: %s", node.name, node.ip, 
                                state.name, node.state.name, 
                                self.get_unhealthy_rules_value(node))
                    else:
                        logger.error("validation failed for node %s", node)
            except:
                logger.exception("failed to run")
            time.sleep(self.interval)

    def validate(self, node):
        """Validate (and correct if needed) the node status. Returns True if
        the node is validated (corrected if necessary), False otherwise.
        """
        if node.state != State.IN_SERVICE and node.unschedulable is False:
            if self.from_any_to_out_of_pool(node):
                return True
            else:
                return False
        return True

    def update(self, node):
        """Defines the status change of node.

        IN_SERVICE --check_health True--> IN_SERVICE
                  \--check_health False--> OUT_OF_POOL

        OUT_OF_POOL --prepare True--> READ_FOR_REPAIR
                   \--prepare False--> OUT_OF_POOL

        READ_FOR_REPAIR --send_repair_request True--> IN_REPAIR
                       \--send_repair_request False--> READ_FOR_REPAIR

        IN_REPAIR --check_liveness True--> AFTER_REPAIR
                 \--check_liveness False--> IN_REPAIR

        AFTER_REPAIR --check_health True--> IN_SERVICE
                    \--check_health False--> OUT_OF_POOL

        FIXME:
        check_health may return False even if check_liveness returns True.
        This can happen when metrics have not get populated into Prometheus.
        """
        try:
            if node.state == State.IN_SERVICE:
                if self.check_health(node) is False:
                    self.from_in_service_to_out_of_pool(node)
            elif node.state == State.OUT_OF_POOL:
                if self.prepare(node):
                    self.from_out_of_pool_to_ready_for_repair(node)
            elif node.state == State.READY_FOR_REPAIR:
                if self.send_repair_request(node):
                    self.from_ready_for_repair_to_in_repair(node)
            elif node.state == State.IN_REPAIR:
                if self.check_liveness(node):
                    self.from_in_repair_to_after_repair(node)
            elif node.state == State.AFTER_REPAIR:
                if self.check_health(node, stat="current"):
                    self.from_after_repair_to_in_service(node)
                else:
                    self.from_after_repair_to_out_of_pool(node)
            else:
                logger.error("Node % has unrecognized state", node)
        except:
            logger.exception("Exception in step for node %s", node)

    def check_health(self, node, stat=None):
        """Check the health against all rules."""
        unhealthy_rules = []
        for rule in self.rules:
            if not rule.check_health(node, stat):
                unhealthy_rules.append(rule)
        node.unhealthy_rules = unhealthy_rules
        return len(unhealthy_rules) == 0

    def prepare(self, node):
        """Prepare for each rule"""
        for rule in node.unhealthy_rules:
            if not rule.prepare(node):
                return False
        return True

    def send_repair_request(self, node):
        """Send the list of unhealthy rules to Agent"""
        url = urllib.parse.urljoin(
            "http://%s:%s" % (node.ip, self.agent_port), "/repair")

        if not isinstance(node.unhealthy_rules, list) or \
                len(node.unhealthy_rules) == 0:
            logger.debug("nothing in unhealthy_rules for %s", url)
            return True

        repair_rules = [
            rule.__class__.__name__ for rule in node.unhealthy_rules]
        try:
            resp = requests.post(url, json=repair_rules)
            code = resp.status_code
            logger.debug(
                "sent repair request to %s: %s, %s. response: %s", node.name,
                url, repair_rules, code)
            return code == 200
        except ConnectionError:
            logger.error(
                "connection error when sending repair request to %s: %s, %s",
                node.name, url, repair_rules)
        except:
            logger.exception(
                "failed to send repair request to %s: %s, %s", node.name, url,
                repair_rules)
        return False

    def check_liveness(self, node):
        """Check the liveness of Agent"""
        url = urllib.parse.urljoin(
            "http://%s:%s" % (node.ip, self.agent_port), "/liveness")
        try:
            resp = requests.get(url)
            code = resp.status_code
            logger.debug(
                "sent liveness request to %s: %s. response: %s", 
                node.name, url, code)
            return code == 200
        except ConnectionError:
            logger.error(
                "connection error when sending liveness request to %s: %s",
                node.name, url)
        except:
            logger.exception(
                "failed to send liveness request to %s: %s", node.name, url)
        return False

    def get_unhealthy_rules_value(self, node):
        """Get string value of unhealth rules for node."""
        if not isinstance(node.unhealthy_rules, list) or \
                len(node.unhealthy_rules) == 0:
            value = None
        else:
            value = ",".join([rule.__class__.__name__
                              for rule in node.unhealthy_rules])
        return value

    def patch(self, node, unschedulable=None, labels=None, annotations=None):
        """Patch unschedulable, labels, annotations at one go. This is to
        ensure that the repair state change is atomic for a node.
        """
        if self.dry_run:
            logger.info(
                "node %s (%s) dry run. current state: %s, current "
                "unschedulable: %s, target unschedulable: %s, target "
                "labels: %s, target annotations: %s", node.name, node.ip, 
                node.state.name, node.unschedulable, unschedulable, labels, 
                annotations)
            return True

        return self.k8s_util.patch_node(
            node.name, unschedulable, labels, annotations)

    def from_any_to_out_of_pool(self, node):
        """Move from any state into OUT_OF_POOL"""
        unschedulable = True
        labels = {REPAIR_STATE: State.OUT_OF_POOL.name}
        annotations = {
            REPAIR_STATE_LAST_UPDATE_TIME: str(datetime.datetime.utcnow()),
            REPAIR_UNHEALTHY_RULES: None,
        }
        if self.patch(node, unschedulable=unschedulable, labels=labels,
                      annotations=annotations):
            node.unschedulable = unschedulable
            node.state = State.OUT_OF_POOL
            return True
        else:
            return False

    def from_in_service_to_out_of_pool(self, node):
        """Move from IN_SERVICE into OUT_OF_POOL"""
        unschedulable = True
        labels = {REPAIR_STATE: State.OUT_OF_POOL.name}
        annotations = {
            REPAIR_STATE_LAST_UPDATE_TIME: str(datetime.datetime.utcnow()),
            REPAIR_UNHEALTHY_RULES: self.get_unhealthy_rules_value(node),
        }
        if self.patch(node, unschedulable=unschedulable, labels=labels,
                      annotations=annotations):
            node.unschedulable = unschedulable
            node.state = State.OUT_OF_POOL
            return True
        else:
            return False

    def from_out_of_pool_to_ready_for_repair(self, node):
        """Move from OUT_OF_POOL into READY_FOR_REPAIR"""
        labels = {REPAIR_STATE: State.READY_FOR_REPAIR.name}
        annotations = {
            REPAIR_STATE_LAST_UPDATE_TIME: str(datetime.datetime.utcnow()),
        }
        if self.patch(node, labels=labels, annotations=annotations):
            node.state = State.READY_FOR_REPAIR
            return True
        else:
            return False

    def from_ready_for_repair_to_in_repair(self, node):
        """Move from READY_FOR_REPAIR into IN_REPAIR"""
        labels = {REPAIR_STATE: State.IN_REPAIR.name}
        annotations = {
            REPAIR_STATE_LAST_UPDATE_TIME: str(datetime.datetime.utcnow()),
        }
        if self.patch(node, labels=labels, annotations=annotations):
            node.state = State.IN_REPAIR
            return True
        else:
            return False

    def from_in_repair_to_after_repair(self, node):
        """Move from IN_REPAIR into AFTER_REPAIR"""
        labels = {REPAIR_STATE: State.AFTER_REPAIR.name}
        annotations = {
            REPAIR_STATE_LAST_UPDATE_TIME: str(datetime.datetime.utcnow()),
        }
        if self.patch(node, labels=labels, annotations=annotations):
            node.state = State.AFTER_REPAIR
            return True
        else:
            return False

    def from_after_repair_to_in_service(self, node):
        """Move from AFTER_REPAIR into IN_SERVICE"""
        unschedulable = False
        labels = {REPAIR_STATE: State.IN_SERVICE.name}
        annotations = {
            REPAIR_STATE_LAST_UPDATE_TIME: str(datetime.datetime.utcnow()),
            REPAIR_UNHEALTHY_RULES: None,
        }
        if self.patch(node, unschedulable=unschedulable, labels=labels,
                      annotations=annotations):
            node.unschedulable = unschedulable
            node.state = State.IN_SERVICE
            return True
        else:
            return False

    def from_after_repair_to_out_of_pool(self, node):
        """Move from AFTER_REPAIR into OUT_OF_POOL"""
        labels = {REPAIR_STATE: State.OUT_OF_POOL.name}
        annotations = {
            REPAIR_STATE_LAST_UPDATE_TIME: str(datetime.datetime.utcnow()),
            REPAIR_UNHEALTHY_RULES: self.get_unhealthy_rules_value(node),
        }
        if self.patch(node, labels=labels, annotations=annotations):
            node.state = State.OUT_OF_POOL
            return True
        else:
            return False


def get_config(config_path):
    with open(os.path.join(config_path, "config.yaml"), "r") as f:
        config = yaml.safe_load(f)
    return config


def main(params):
    register_stack_trace_dump()

    logger.info("Starting repairmanager ...")
    try:
        rules = instantiate_rules()
        config = get_config(params.config)
        k8s_util = K8sUtil()
        rest_util = RestUtil()
        repair_manager = RepairManager(
            rules, config, int(params.agent_port), k8s_util, rest_util,
            interval=params.interval, dry_run=params.dry_run)
        repair_manager.run()
    except:
        logger.exception("Exception in repairmanager run")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config",
                        "-c",
                        help="directory path containing config.yaml",
                        default="/etc/repairmanager")
    parser.add_argument("--log",
                        "-l",
                        help="log dir to store log",
                        default="/var/log/repairmanager")
    parser.add_argument("--interval",
                        "-i",
                        help="sleep time between repairmanager runs",
                        default=30,
                        type=int)
    parser.add_argument("--port",
                        "-p",
                        help="port for repairmanager",
                        default=9080)
    parser.add_argument("--agent_port",
                        "-a",
                        help="port for repairmanager agent",
                        default=9081)
    parser.add_argument("--dry_run",
                        "-d",
                        action="store_true",
                        help="dry run flag")
    args = parser.parse_args()

    console_handler = logging.StreamHandler()
    file_handler = handlers.RotatingFileHandler(
        os.path.join(args.log, "repairmanager.log"),
        maxBytes=10240000, backupCount=10)
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(threadName)s - %(filename)s:%(lineno)s - %(message)s",
        level=get_logging_level(),
        handlers=[console_handler, file_handler])

    main(args)
