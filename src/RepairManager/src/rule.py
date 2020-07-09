#!/usr/bin/env python3

import logging
import os
import subprocess

from util import State, RestUtil, PrometheusUtil, walk_json

logger = logging.getLogger(__name__)


CHROOT_HOST_FS = ["chroot", "/host-fs"]


def override(func):
    """Return the func itself. Serves as an override decorator."""
    return func


def exec_cmd(command, timeout=None):
    """Execute one command"""
    if timeout is None:
        # default to a large 15 min.
        # E.g. kubelet sometimes takes a long time to restart
        timeout = 900
    command = CHROOT_HOST_FS + command
    logger.info("executing: %s", command)
    try:
        output = subprocess.check_output(command, stderr=subprocess.STDOUT,
                                         timeout=timeout).decode("utf-8")
        logger.info("%s output: %s", command, output)
        return True
    except subprocess.TimeoutExpired:
        logger.warning("%s timeout", command)
    except subprocess.CalledProcessError as e:
        logger.warning("%s returns %d, output %s", e.returncode, e.output)
    except Exception:
        logger.exception("%s failed")
    return False


class Rule(object):
    """Base class for different rules.

    check_health is invoked by RepairManager to check the health of a node
    against the rule. If unhealthy, RepairManager will move the node from
    IN_SERVICE to OUT_OF_POOL.

    prepare is invoked by RepairManager to prepare the node for repair. If
    successful, RepairManager will move the node from OUT_OF_POOL to
    READY_FOR_REPAIR.

    repair is invoked by RepairManagerAgent to carry out the actual repair on
    the node.
    """
    subclasses = {}  # Stores all subclasses

    @classmethod
    def register_subclass(cls, rule_name):
        """Subclass register for keeping a map of subclasses.

        This avoids the need to add to static map every time a new subclass
        is added.

        Args:
            rule_name: A string indicating the name of the rule.

        Returns:
            A decorator for registering subclasses.
        """
        def decorator(subclass):
            cls.subclasses[rule_name] = subclass
            return subclass
        return decorator

    def __init__(self, metrics, stat="avg", interval="5m", wait_for_jobs=True,
                 desc=""):
        """Constructs a Rule instance.

        Args:
            metrics: A list of metrics.
            stat: avg, min, max, etc. supported by <stat>_over_time query
                in Prometheus.
            interval: The look-back time interval for stat.
            wait_for_jobs: Whether repair needs to wait for jobs to finish.
            desc: Short description on what the rule detects
        """
        self.metrics = metrics
        self.stat = stat
        self.interval = interval
        self.wait_for_jobs = wait_for_jobs
        self.desc = desc
        self.data = {"current": {}, stat: {}}
        self.prometheus_util = PrometheusUtil()

    @property
    def name(self):
        return self.__class__.__name__

    @override
    def update_data(self):
        """Refresh data for metrics from Prometheus source.

        Returns:
            None
        """
        for metric in self.metrics:
            query_current = metric
            resp = self.prometheus_util.query(query_current)
            self.data["current"][metric] = walk_json(resp, "data", "result")

            query_over_time = \
                "%s_over_time(%s[%s])" % (self.stat, metric, self.interval)
            resp = self.prometheus_util.query(query_over_time)
            self.data[self.stat][metric] = walk_json(resp, "data", "result")

    def check_health(self, node, stat=None):
        """Check the health for the node against this rule.

        Calls the actual implementation check_health_impl.

        Args:
            node: Node object containing info on node.
            stat: avg, min, max, etc. supported by <stat>_over_time query
                in Prometheus.

        Returns:
            True if check_health_impl returns True, False otherwise.
        """
        if stat is None:
            stat = self.stat
        return self.check_health_impl(node, stat)

    @override
    def check_health_impl(self, node, stat):
        """The actual implementation of health check.

        Args:
            node: Node object containing info on node.
            stat: avg, min, max, etc. supported by <stat>_over_time query
                in Prometheus.

        Returns:
            True if the node is healthy by the rule, False otherwise.
        """
        # By default, always return True.
        return True

    def prepare(self, node):
        """Wait for all jobs to finish if necessary.

        Args:
            node: Node object containing info on node.

        Returns:
            True if prepare is successful, False otherwise.
        """
        if self.wait_for_jobs:
            if len(node.jobs) > 0:
                return False
        return True

    @override
    def repair(self):
        """Repair action invoked by RepairManagerAgent.

        Upon receiving repair signal, RepairManagerAgent execute the
        corresponding repair action.

        Returns:
            None
        """
        # By default, reboot the node
        if exec_cmd(["sync"]) is False:
            logger.error("sync failed")
            return False

        if exec_cmd(["reboot", "-f"]) is False:
            logger.error("reboot -f failed")
            return False

        return True


@Rule.register_subclass("UnschedulableRule")
class UnschedulableRule(Rule):
    """Rule for nodes marked as unschedulable."""
    def __init__(self):
        super(UnschedulableRule, self).__init__(["unschedulable"],
                                                desc="unschedulable")

    def update_data(self):
        # The rule does not depend on external data source.
        pass

    def check_health_impl(self, node, stat):
        # Unhealthy if node is IN_SERVICE but marked as unschedulable
        if node.state == State.IN_SERVICE and node.unschedulable is True and \
                node.repair_cycle is True:
            return False
        else:
            return True


@Rule.register_subclass("K8sGpuRule")
class K8sGpuRule(Rule):
    """Rule for GPU numbers on the node"""
    def __init__(self):
        super(K8sGpuRule, self).__init__(
            ["k8s_node_gpu_total", "k8s_node_gpu_allocatable"],
            wait_for_jobs=False, desc="GPU misreport")

    def check_health_impl(self, node, stat):
        # k8s_node_gpu_allocatable shows 0 for any unschedulable node.
        # Use gpu info from k8s to check health.

        # Unhealthy if expected > total or total > allocatable
        try:
            gpu_expected = int(node.gpu_expected)
            gpu_total = int(node.gpu_total)
            gpu_allocatable = int(node.gpu_allocatable)
            if gpu_expected > gpu_total or gpu_total > gpu_allocatable:
                return False
            else:
                return True
        except:
            logger.exception("check health failed")
        return False

    def repair(self):
        # Restart kubelet service
        if exec_cmd(["systemctl", "restart", "kubelet"]) is False:
            logger.error("systemctl restart kubelet failed")
            return False
        return True


@Rule.register_subclass("DcgmEccDBERule")
class DcgmEccDBERule(Rule):
    """Rule for ECC DBE on the node."""
    def __init__(self):
        super(DcgmEccDBERule, self).__init__(["dcgm_ecc_dbe_volatile_total"],
                                             desc="uncorrectable ECC error")

    def get_values(self, node, metric, stat):
        values = []
        for item in self.data[stat].get(metric, []):
            instance = item.get("metric", {}).get("instance")
            instance_ip = instance.split(":")[0]
            if node.ip == instance_ip:
                values.append(float(item.get("value")[1]))
        return values

    def check_health_impl(self, node, stat):
        # Unhealthy if there is a ECC DBE on any of the GPUs on the node.
        try:
            values = self.get_values(node, "dcgm_ecc_dbe_volatile_total", stat)
            for value in values:
                if value > 0:
                    return False
            return True
        except:
            logger.exception("check health failed")
        return False


@Rule.register_subclass("InfinibandRule")
class InfinibandRule(Rule):
    """Rule for Infiniband on the node."""
    def __init__(self):
        super(InfinibandRule, self).__init__(["infiniband_up"],
                                             desc="bad IB device")

    def get_values(self, node, metric, stat):
        values = {}
        for item in self.data[stat].get(metric, []):
            instance = item.get("metric", {}).get("instance")
            instance_ip = instance.split(":")[0]
            if node.ip == instance_ip:
                device = item.get("metric", {}).get("device")
                port = item.get("metric", {}).get("port")
                values["%s:%s" % (device, port)] = float(item.get("value")[1])
        return values

    def check_health_impl(self, node, stat):
        # Healthy if there is no Infiniband device on the node.
        if node.infiniband is None:
            return True

        if not isinstance(node.infiniband, list):
            logger.warning("infiniband in %s is not a list.", node)
            return True

        # Unhealthy if there is an infiniband device down.
        try:
            values = self.get_values(node, "infiniband_up", stat)
            for infiniband in node.infiniband:
                if values.get(infiniband) != 1:
                    return False
            return True
        except:
            logger.exception("check health failed")
        return False


@Rule.register_subclass("IPoIBRule")
class IPoIBRule(Rule):
    """Rule for IPoIB interface on the node."""
    def __init__(self):
        super(IPoIBRule, self).__init__(["ipoib_up"], wait_for_jobs=False,
                                        desc="bad IPoIB")

    def get_values(self, node, metric, stat):
        values = {}
        for item in self.data[stat].get(metric, []):
            instance = item.get("metric", {}).get("instance")
            instance_ip = instance.split(":")[0]
            if node.ip == instance_ip:
                device = item.get("metric", {}).get("device")
                values["%s" % device] = float(item.get("value")[1])
        return values

    def check_health_impl(self, node, stat):
        # Healthy if there is no IPoIB interface on the node.
        if node.ipoib is None:
            return True

        if not isinstance(node.ipoib, list):
            return True

        # Unhealthy if there is an IBpIB interface down.
        try:
            values = self.get_values(node, "ipoib_up", stat)
            for ipoib in node.ipoib:
                if values.get(ipoib) != 1:
                    return False
            return True
        except:
            logger.exception("check health failed")
        return False

    def repair(self):
        # walinuxagent manages the IPoIB on Azure VM. Restarting it usually
        # fix the IPoIB on Azure VM.
        # For on-premise node, repair will always fail and the noe will get
        # stuck in repair cycle, requiring manual fix.
        if exec_cmd(["systemctl", "restart", "walinuxagent"]) is False:
            logger.error("systemctl restart walinuxagent failed")
            return False
        return True


@Rule.register_subclass("NvPeerMemRule")
class NvPeerMemRule(Rule):
    """Rule for nv_peer_mem module on the node."""
    def __init__(self):
        super(NvPeerMemRule, self).__init__(["nv_peer_mem_count"],
                                            wait_for_jobs=False,
                                            desc="bad GPUDirect")

    def get_value(self, node, metric, stat):
        for item in self.data[stat].get(metric, []):
            instance = item.get("metric", {}).get("instance")
            instance_ip = instance.split(":")[0]
            if node.ip == instance_ip:
                return float(item.get("value")[1])
        return None

    def check_health_impl(self, node, stat):
        # Healthy if node does not have nv_peer_mem module
        if node.nv_peer_mem is None:
            return True

        # Unhealthy if nv_peer_mem is down.
        try:
            expected_count = int(node.nv_peer_mem)
            count = self.get_value(node, "nv_peer_mem_count", stat)
            if count != expected_count:
                return False
            else:
                return True
        except:
            logger.exception("check health failed")
        return False

    def repair(self):
        # Restarting nv_peer_mem can restore the module.
        if exec_cmd(["systemctl", "restart", "nv_peer_mem"]) is False:
            logger.error("systemctl restart nv_peer_mem failed")
            return False
        return True


@Rule.register_subclass("NVSMRule")
class NVSMRule(Rule):
    """Rule for NVSM health check on the node."""
    def __init__(self):
        super(NVSMRule, self).__init__(
            ["nvsm_health_total_count", "nvsm_health_good_count"],
            stat="max", interval="10m", desc="unhealthy by NVSM")

    def get_value(self, node, metric, stat):
        for item in self.data[stat].get(metric, []):
            instance = item.get("metric", {}).get("instance")
            instance_ip = instance.split(":")[0]
            if node.ip == instance_ip:
                return float(item.get("value")[1])
        return None

    def check_health_impl(self, node, stat):
        # Healthy if there is not NVSM on the node.
        if node.nvsm is None:
            return True

        # Unhealthy if good < total in NVSM health check.
        try:
            total = self.get_value(node, "nvsm_health_total_count", stat)
            good = self.get_value(node, "nvsm_health_good_count", stat)
            if good < total:
                return False
            else:
                return True
        except:
            logger.exception("check health failed")
        return False

    def repair(self):
        # Get a health dump and reboot.
        os.environ["TERM"] = "xterm"
        # Give nvsm dump health sufficient time to dump
        if exec_cmd(["nvsm", "dump", "health"], timeout=3600) is False:
            logger.error("nvsm dump health (with timeout 3600s) failed")
            return False

        if exec_cmd(["sync"]) is False:
            logger.error("sync failed")
            return False

        if exec_cmd(["reboot", "-f"]) is False:
            logger.error("reboot -f failed")
            return False

        return True


def instantiate_rules():
    """Return a list of rule instances for all subclasses"""
    rules = []
    for rule_name in Rule.subclasses:
        rules.append(Rule.subclasses[rule_name]())
    return rules
