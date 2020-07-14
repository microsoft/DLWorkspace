#!/usr/bin/env python3

import argparse
import collections
import datetime
import logging
import os
import prometheus_client
import requests
import threading
import time
import urllib.parse
import yaml

from flask import Flask, Response
from flask_cors import CORS
from logging import handlers
from prometheus_client.core import REGISTRY, GaugeMetricFamily
from requests.exceptions import ConnectionError
from constant import REPAIR_STATE, REPAIR_CYCLE, REPAIR_MESSAGE, \
    REPAIR_STATE_LAST_UPDATE_TIME, REPAIR_STATE_LAST_EMAIL_TIME, \
    REPAIR_UNHEALTHY_RULES
from util import State, AtomicRef, K8sUtil, RestUtil, PrometheusUtil, \
    register_stack_trace_dump, get_logging_level, parse_for_jobs_and_nodes, \
    walk_json
from rule import instantiate_rules, UnschedulableRule
from email_handler import EmailHandler

logger = logging.getLogger(__name__)


def utcnow():
    return datetime.datetime.timestamp(datetime.datetime.utcnow())


class CustomCollector(object):
    """Custom collector object for Prometheus scraping"""
    def __init__(self, ref):
        self.ref = ref

    def collect(self):
        metrics = self.ref.get()
        if metrics is not None:
            for metric in metrics:
                yield metric


class RepairManager(object):
    """RepairManager controls the logic of repair cycle of each worker node.
    """
    def __init__(self, rules, config, port, agent_port, k8s_util, rest_util,
                 interval=30, dry_run=False, email_handler=None):
        self.rules = rules
        self.config = config
        self.port = port
        self.agent_port = agent_port
        self.dry_run = dry_run

        self.email_handler = email_handler
        self.k8s_util = k8s_util
        self.rest_util = rest_util
        self.interval = interval

        self.jobs = []
        self.nodes = []

        self.atomic_ref = AtomicRef()
        self.handler = threading.Thread(
            target=self.handle, name="handler", daemon=True)

        # Allow some time for metrics/info to come up to latest
        self.grace_period = int(
            config.get("repair-manager", {}).get("grace_period", 5 * 60))

        # Send email every few hours
        self.email_interval = int(
            config.get("repair-manager", {}).get("email_interval", 4 * 60 * 60))

        self.cluster_name = config.get("cluster_name")
        self.dashboard_url = config.get("dashboard_url")

    def run(self):
        self.handler.start()
        self.serve()

    def serve(self):
        REGISTRY.register(CustomCollector(self.atomic_ref))

        app = Flask(self.__class__.__name__)
        CORS(app)

        @app.route("/metrics")
        def metrics():
            return Response(prometheus_client.generate_latest(),
                            mimetype="text/plain; version=0.0.4; charset=utf-8")

        app.run(host="0.0.0.0", port=self.port, debug=False, use_reloader=False)

    def handle(self):
        # Main loop for repair cycle of nodes.
        while True:
            try:
                # Get refresh repair state
                self.get_repair_state()

                # Update repair state for nodes
                logger.info(
                    "Running repair update on %s nodes against rules: %s",
                    len(self.nodes), [rule.name for rule in self.rules])
                for node in self.nodes:
                    if self.validate(node):
                        state = node.state
                        self.update(node)
                        if node.state != state:
                            logger.info(
                                "node %s (%s) repair state: %s -> %s. "
                                "unhealthy rules: %s", node.name, node.ip, 
                                state.name, node.state_name,
                                self.get_unhealthy_rules_value(node))
                    else:
                        logger.error("validation failed for node %s", node)

                # Update metrics for Prometheus scraping
                self.update_metrics()

                # Update unhealthy nodes for jobs
                self.update_unhealthy_nodes_for_jobs()

                # Update repair message for jobs in DB
                self.update_repair_message_for_jobs()

                # Send emails to users whose jobs are affected
                self.send_emails()

                # Clean up terminating-timeout pods if any
                self.clean_up_terminating_timeout_pods()
            except:
                logger.exception("failed to run")
            time.sleep(self.interval)

    def get_repair_state(self):
        """Refresh active jobs from DB. Refresh nodes based on new info from
        kubernetes and DB. Refresh metrics data in rules from Prometheus.
        """
        try:
            job_list = self.rest_util.get_active_jobs()
            vc_list = self.rest_util.list_vcs().get("result", {})
            k8s_nodes = self.k8s_util.list_node()
            k8s_pods = self.k8s_util.list_pods()
            self.jobs, self.nodes = parse_for_jobs_and_nodes(
                job_list, vc_list, k8s_nodes, k8s_pods, self.rules, self.config)

            [rule.update_data() for rule in self.rules]
        except:
            logger.exception("failed to get repair state")
            self.jobs = []
            self.nodes = []

    def update_metrics(self):
        sku_list = set([node.sku for node in self.nodes])

        # Count nodes by repair state (repair state -> {sku: count})
        state_gauge = GaugeMetricFamily(
            "repair_state_node_count",
            "node count in different repair states",
            labels=["repair_state", "sku"])

        state_node_count = collections.defaultdict(
            lambda: collections.defaultdict(lambda: 0))
        for state in State:
            for sku in sku_list:
                state_node_count[state.name][sku] = 0

        for node in self.nodes:
            state_node_count[node.state_name][node.sku] += 1

        for state, count_by_sku in state_node_count.items():
            for sku, count in count_by_sku.items():
                state_gauge.add_metric([state, sku], count)

        # Count nodes by repair rule (repair rule -> {sku: count})
        rule_gauge = GaugeMetricFamily(
            "repair_rule_node_count",
            "node count in different repair rules",
            labels=["repair_rule", "sku"])

        rule_node_count = collections.defaultdict(
            lambda: collections.defaultdict(lambda: 0))
        for rule in self.rules:
            for sku in sku_list:
                rule_node_count[rule.name][sku] = 0

        for node in self.nodes:
            for rule in node.unhealthy_rules:
                rule_node_count[rule.name][node.sku] += 1

        for rule, count_by_rule in rule_node_count.items():
            for sku, count in count_by_rule.items():
                rule_gauge.add_metric([rule, sku], count)

        # Count jobs impacted by repair (sku -> count)
        jobs_gauge = GaugeMetricFamily(
            "repair_impacted_job_count",
            "Number of jobs impacted by repair",
            labels=["sku"])

        impacted_job_count = collections.defaultdict(lambda: 0)
        for sku in sku_list:
            impacted_job_count[sku] = 0

        for job in self.jobs:
            job_sku = set([node.sku for _, node in job.unhealthy_nodes.items()])
            for sku in job_sku:
                impacted_job_count[sku] += 1

        for sku, count in impacted_job_count.items():
            jobs_gauge.add_metric([sku], count)

        self.atomic_ref.set([state_gauge, rule_gauge, jobs_gauge])

    def update_unhealthy_nodes_for_jobs(self):
        """Update unhealthy nodes for jobs after a step in repair manager"""
        for node in self.nodes:
            if node.state == State.IN_SERVICE:
                continue
            for job_id, job in node.jobs.items():
                if node.name not in job.unhealthy_nodes:
                    job.unhealthy_nodes[node.name] = node

    def update_repair_message_for_job(self, job_id, repair_message):
        try:
            resp = self.rest_util.update_repair_message(job_id, repair_message)
            if resp.status_code == 200:
                logger.info(
                    "successfully updated repair message for job %s", job_id)
            else:
                logger.error(
                    "failed to update repair message %s for job %s",
                    repair_message, job_id)
        except:
            logger.exception(
                "failed to update repair message for job %s", job_id)

    def update_repair_message_for_jobs(self):
        """Update repair message for active jobs in DB"""
        timestamp = utcnow()
        for job in self.jobs:
            if len(job.unhealthy_nodes) > 0:
                msg = "The job is running on unhealthy node(s): "
                node_msgs = []
                for name, node in job.unhealthy_nodes.items():
                    desc = self.get_unhealthy_rules_desc(node)
                    node_msgs.append("%s (%s)" % (name, desc))
                msg += ", ".join(node_msgs) + ". "

                msg += "Please check if it is still running as expected. "
                if job.wait_for_jobs:
                    msg += "Node(s) repair is waiting for the job to finish. Please kill/finish the job to expedite node(s) repair."
                else:
                    msg += "Restart/resubmit your job if necessary."
                message = {
                    "timestamp": timestamp,
                    "message": ["CRITICAL", msg, ""]
                }
            else:
                # Clear repair message if node becomes healthy or job gets
                # rescheduled onto a healthy node
                message = {}
            self.update_repair_message_for_job(job.job_id, message)

    def send_emails(self):
        """Send alert emails to users"""
        if self.email_handler is None:
            logger.info("email handler is not set up.")
            return

        now = utcnow()
        for node in self.nodes:
            if node.state == State.IN_SERVICE:
                continue

            if node.last_email_time and \
                    (float(node.last_email_time) + self.email_interval) > now:
                logger.debug("last email time %s, now %s, email interval %s",
                             node.last_email_time, now, self.email_interval)
                continue

            # Send email for each job on the node
            for job_id, job in node.jobs.items():
                subject = "[DLTS Job Alert][%s/%s] %s is running on an unhealthy node" % \
                    (job.vc_name, self.cluster_name, job_id)
                job_link = "https://%s/jobs/%s/%s" % \
                    (self.dashboard_url, self.cluster_name, job_id)
                msg = "The job <a href=%s>%s</a> is running on an unhealthy node <b>%s</b> (%s). " % \
                    (job_link, job_id, node.name,
                     self.get_unhealthy_rules_desc(node))
                msg += "Please check if it is still running as expected. "
                if job.wait_for_jobs:
                    msg += "Node repair is waiting for the job to finish. Please kill/finish the job to expedite node repair."
                else:
                    msg += "Restart/resubmit your job if necessary."
                body = "<p>%s</p>" % msg
                self.email_handler.send(subject, job.username, body)

            # Update the last email time of the node to current
            self.update_last_email_time(node)

    def clean_up_terminating_timeout_pods(self):
        try:
            prometheus_util = PrometheusUtil()
            metric = "k8s_pod_count{type='job',phase='terminating-timeout'}"
            query = "min_over_time(%s[10m])" % metric
            resp = prometheus_util.query(query)
            result = walk_json(resp, "data", "result")
            for item in result:
                pod_name = item.get("metric", {}).get("name")
                if pod_name is not None:
                    logger.info("deleting terminating-timeout pod %s", pod_name)
                    self.k8s_util.delete_pod(pod_name)
        except:
            logger.exception("error occured when cleaning up terminating "
                             "timeout pods")

    def validate(self, node):
        """Validate (and correct if needed) the node status. Returns True if
        the node is validated (corrected if necessary), False otherwise.
        """
        # Repair cycle states: OUT_OF_POOL, READY_FOR_REPAIR, IN_REPAIR,
        # AFTER_REPAIR.
        # Non repair cycle states: OUT_OF_POOL_UNTRACKED (excluding IN_SERVICE)
        if node.state != State.IN_SERVICE and node.unschedulable is False:
            # If a schedulable node is in repair cycle, reset it to OUT_OF_POOL
            if node.repair_cycle is True:
                if self.from_any_to_out_of_pool(node):
                    return True
                else:
                    return False
            # If a schedulable node is not in repair cycle but in repair cycle
            # states, reset it to OUT_OF_POOL_UNTRACKED
            elif node.state != State.OUT_OF_POOL_UNTRACKED:
                if self.from_any_to_out_of_pool_untracked(node):
                    return True
                else:
                    return False
        return True

    def update(self, node):
        """Defines the status change of node.

        IN_SERVICE --unschedulable, not in repair cycle--> OUT_OF_POOL_UNTRACKED
                  \--check_health True--> IN_SERVICE
                  \--check_health False--> OUT_OF_POOL

        OUT_OF_POOL_UNTRACKED --unschedulable, not in repair cycle--> OUT_OF_POOL_UNTRACKED
                             \--schedulable --> IN_SERVICE
                             \--unschedulable, in repair cycle--> OUT_OF_POOL

        OUT_OF_POOL --unschedulable, not in repair cycle--> OUT_OF_POOL_UNTRACKED
                   \--prepare True--> READ_FOR_REPAIR
                   \--prepare False--> OUT_OF_POOL

        READ_FOR_REPAIR --unschedulable, not in repair cycle--> OUT_OF_POOL_UNTRACKED
                       \--send_repair_request True--> IN_REPAIR
                       \--send_repair_request False--> READ_FOR_REPAIR

        IN_REPAIR --unschedulable, not in repair cycle--> OUT_OF_POOL_UNTRACKED
                 \--check_liveness True--> AFTER_REPAIR
                 \--check_liveness False--> IN_REPAIR

        AFTER_REPAIR --unschedulable, not in repair cycle--> OUT_OF_POOL_UNTRACKED
                    \--check_health True--> IN_SERVICE
                    \--check_health False--> OUT_OF_POOL
        """
        try:
            # Any repair state can be moved to OUT_OF_POOL_UNTRACKED so that
            # admin can stop repair cycle any time to do manual repair.
            if node.state != State.OUT_OF_POOL_UNTRACKED:
                if node.unschedulable and (not node.repair_cycle):
                    self.from_any_to_out_of_pool_untracked(node)
                    return

            if node.state == State.IN_SERVICE:
                if self.check_health(node) is False:
                    self.from_in_service_to_out_of_pool(node)
            elif node.state == State.OUT_OF_POOL_UNTRACKED:
                if not node.unschedulable:
                    self.from_out_of_pool_untracked_to_in_service(node)
                elif node.repair_cycle:
                    self.from_out_of_pool_untracked_to_out_of_pool(node)
            elif node.state == State.OUT_OF_POOL:
                if self.prepare(node):
                    self.from_out_of_pool_to_ready_for_repair(node)
                else:
                    self.from_out_of_pool_to_out_of_pool(node)
            elif node.state == State.READY_FOR_REPAIR:
                if self.send_repair_request(node):
                    self.from_ready_for_repair_to_in_repair(node)
            elif node.state == State.IN_REPAIR:
                if self.check_liveness(node):
                    self.from_in_repair_to_after_repair(node)
            elif node.state == State.AFTER_REPAIR:
                healthy = self.check_health(node, stat="current")
                try:
                    now = utcnow()
                    last_update_time = float(node.last_update_time)
                    elapsed = now - last_update_time
                except:
                    elapsed = None

                if elapsed is None:
                    if healthy:
                        self.from_after_repair_to_in_service(node)
                    else:
                        self.from_after_repair_to_out_of_pool(node)
                else:
                    if healthy:
                        self.from_after_repair_to_in_service(node)
                    elif not healthy and elapsed > self.grace_period:
                        self.from_after_repair_to_out_of_pool(node)
                    else:
                        # Do not change state if unhealthy in the grace period
                        pass
            else:
                logger.error("Node %s has unrecognized state", node)
        except:
            logger.exception("Exception in step for node %s", node)

    def check_health(self, node, stat=None):
        """Check the health against all rules."""
        unhealthy_rules = []
        for rule in self.rules:
            if not rule.check_health(node, stat):
                unhealthy_rules.append(rule)

        # Adjust unhealthy rules for nodes
        node.unhealthy_rules = unhealthy_rules
        return len(node.unhealthy_rules) == 0

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

        repair_rules = [rule.name for rule in node.unhealthy_rules]
        try:
            resp = requests.post(url, json=repair_rules, timeout=3)
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
            resp = requests.get(url, timeout=3)
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

    def get_unhealthy_rules_desc(self, node):
        """Get description of unhealthy rules for node."""
        if not isinstance(node.unhealthy_rules, list) or \
                len(node.unhealthy_rules) == 0:
            value = "under repair by admin"
        else:
            value = ", ".join([rule.desc for rule in node.unhealthy_rules])
        return value

    def get_unhealthy_rules_value(self, node):
        """Get string value of unhealthy rules for node."""
        if not isinstance(node.unhealthy_rules, list) or \
                len(node.unhealthy_rules) == 0:
            value = None
        else:
            value = ",".join([rule.name for rule in node.unhealthy_rules])
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
                node.state_name, node.unschedulable, unschedulable, labels,
                annotations)
            return True

        return self.k8s_util.patch_node(
            node.name, unschedulable, labels, annotations)

    def update_last_email_time(self, node):
        email_time = str(utcnow())
        annotations = {
            REPAIR_STATE_LAST_EMAIL_TIME: email_time,
        }
        if self.patch(node, annotations=annotations):
            node.last_email_time = email_time
            return True
        else:
            return False

    def get_repair_message(self, node, message, attach_rules=True):
        if message is None:
            return None

        if attach_rules:
            return message + " (%s)" % self.get_unhealthy_rules_desc(node)
        else:
            return message

    def from_any_to_out_of_pool(self, node):
        """Move from any state into OUT_OF_POOL"""
        labels = {REPAIR_STATE: State.OUT_OF_POOL.name}
        update_time = str(utcnow())
        # Do not override REPAIR_UNHEALTHY_RULES if present
        # Default to apply UnschedulableRule, which enforces a reboot at repair
        if not isinstance(node.unhealthy_rules, list) or \
                len(node.unhealthy_rules) == 0:
            node.unhealthy_rules = [UnschedulableRule()]
        repair_message = self.get_repair_message(
            node, "Health event(s) detected, out of scheduling pool")
        annotations = {
            REPAIR_STATE_LAST_UPDATE_TIME: update_time,
            REPAIR_UNHEALTHY_RULES: self.get_unhealthy_rules_value(node),
            REPAIR_CYCLE: "True",
            REPAIR_MESSAGE: repair_message,
        }
        if self.patch(node, unschedulable=True, labels=labels,
                      annotations=annotations):
            node.unschedulable = True
            node.state = State.OUT_OF_POOL
            node.last_update_time = update_time
            node.repair_cycle = True
            node.repair_message = repair_message
            return True
        else:
            return False

    def from_any_to_out_of_pool_untracked(self, node):
        """Move from any state into OUT_OF_POOL_UNTRACKED"""
        labels = {REPAIR_STATE: State.OUT_OF_POOL_UNTRACKED.name}
        update_time = str(utcnow())
        repair_message = self.get_repair_message(
            node, "Pending repair by Administrator", attach_rules=False)
        annotations = {
            REPAIR_STATE_LAST_UPDATE_TIME: update_time,
            REPAIR_UNHEALTHY_RULES: None,
            REPAIR_CYCLE: None,
            REPAIR_MESSAGE: repair_message,
        }
        if self.patch(node, unschedulable=True, labels=labels,
                      annotations=annotations):
            node.unschedulable = True
            node.state = State.OUT_OF_POOL_UNTRACKED
            node.last_update_time = update_time
            node.unhealthy_rules = []
            node.repair_cycle = False
            node.repair_message = repair_message
            return True
        else:
            return False

    def from_out_of_pool_untracked_to_in_service(self, node):
        """Move from OUT_OF_POOL_UNTRACKED into IN_SERVICE"""
        labels = {REPAIR_STATE: State.IN_SERVICE.name}
        update_time = str(utcnow())
        annotations = {
            REPAIR_STATE_LAST_UPDATE_TIME: update_time,
            REPAIR_STATE_LAST_EMAIL_TIME: None,
            REPAIR_UNHEALTHY_RULES: None,
            REPAIR_CYCLE: None,
            REPAIR_MESSAGE: None,
        }
        if self.patch(node, unschedulable=False, labels=labels,
                      annotations=annotations):
            node.unschedulable = False
            node.state = State.IN_SERVICE
            node.last_update_time = update_time
            node.last_email_time = None
            node.unhealthy_rules = []
            node.repair_cycle = False
            node.repair_message = None
            return True
        else:
            return False

    def from_out_of_pool_untracked_to_out_of_pool(self, node):
        """Move from OUT_OF_POOL_UNTRACKED into OUT_OF_POOL"""
        return self.from_any_to_out_of_pool(node)

    def from_in_service_to_out_of_pool(self, node):
        """Move from IN_SERVICE into OUT_OF_POOL"""
        return self.from_any_to_out_of_pool(node)

    def from_out_of_pool_to_ready_for_repair(self, node):
        """Move from OUT_OF_POOL into READY_FOR_REPAIR"""
        labels = {REPAIR_STATE: State.READY_FOR_REPAIR.name}
        update_time = str(utcnow())
        repair_message = self.get_repair_message(
            node, "Repair action will start soon")
        annotations = {
            REPAIR_STATE_LAST_UPDATE_TIME: update_time,
            REPAIR_MESSAGE: repair_message,
        }
        if self.patch(node, labels=labels, annotations=annotations):
            node.state = State.READY_FOR_REPAIR
            node.last_update_time = update_time
            node.repair_message = repair_message
            return True
        else:
            return False

    def from_out_of_pool_to_out_of_pool(self, node):
        """Move from any state into OUT_OF_POOL"""
        repair_message = self.get_repair_message(
            node, "Waiting for job(s) to finish before repair")
        annotations = {REPAIR_MESSAGE: repair_message}
        if self.patch(node, annotations=annotations):
            node.repair_message = repair_message
            return True
        else:
            return False

    def from_ready_for_repair_to_in_repair(self, node):
        """Move from READY_FOR_REPAIR into IN_REPAIR"""
        labels = {REPAIR_STATE: State.IN_REPAIR.name}
        update_time = str(utcnow())
        repair_message = self.get_repair_message(node, "Currently under repair")
        annotations = {
            REPAIR_STATE_LAST_UPDATE_TIME: update_time,
            REPAIR_MESSAGE: repair_message,
        }
        if self.patch(node, labels=labels, annotations=annotations):
            node.state = State.IN_REPAIR
            node.last_update_time = update_time
            node.repair_message = repair_message
            return True
        else:
            return False

    def from_in_repair_to_after_repair(self, node):
        """Move from IN_REPAIR into AFTER_REPAIR"""
        labels = {REPAIR_STATE: State.AFTER_REPAIR.name}
        update_time = str(utcnow())
        repair_message = self.get_repair_message(
            node, "Repair completed, pending health check")
        annotations = {
            REPAIR_STATE_LAST_UPDATE_TIME: update_time,
            REPAIR_MESSAGE: repair_message
        }
        if self.patch(node, labels=labels, annotations=annotations):
            node.state = State.AFTER_REPAIR
            node.last_update_time = update_time
            node.repair_message = repair_message
            return True
        else:
            return False

    def from_after_repair_to_in_service(self, node):
        """Move from AFTER_REPAIR into IN_SERVICE"""
        labels = {REPAIR_STATE: State.IN_SERVICE.name}
        update_time = str(utcnow())
        annotations = {
            REPAIR_STATE_LAST_UPDATE_TIME: update_time,
            REPAIR_STATE_LAST_EMAIL_TIME: None,
            REPAIR_UNHEALTHY_RULES: None,
            REPAIR_CYCLE: None,
            REPAIR_MESSAGE: None,
        }
        if self.patch(node, unschedulable=False, labels=labels,
                      annotations=annotations):
            node.unschedulable = False
            node.state = State.IN_SERVICE
            node.last_update_time = update_time
            node.last_email_time = None
            node.unhealthy_rules = []
            node.repair_cycle = False
            node.repair_message = None
            return True
        else:
            return False

    def from_after_repair_to_out_of_pool(self, node):
        """Move from AFTER_REPAIR into OUT_OF_POOL"""
        return self.from_any_to_out_of_pool(node)


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
        try:
            email_handler = EmailHandler(config.get("smtp"))
        except:
            email_handler = None

        repair_manager = RepairManager(rules,
                                       config,
                                       int(params.port),
                                       int(params.agent_port),
                                       k8s_util,
                                       rest_util,
                                       interval=params.interval,
                                       dry_run=params.dry_run,
                                       email_handler=email_handler)
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
