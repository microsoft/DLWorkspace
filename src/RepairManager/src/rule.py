#!/usr/bin/env python3

import logging
import os

from util import RestUtil, PrometheusUtil, walk_json

logger = logging.getLogger(__name__)


def override(func):
    return func


class Rule(object):
    subclasses = {}

    @classmethod
    def register_subclass(cls, rule_name):
        def decorator(subclass):
            cls.subclasses[rule_name] = subclass
            return subclass
        return decorator

    def __init__(self, metrics, interval="5m"):
        self.metrics = metrics if isinstance(metrics, list) else [metrics]
        self.interval = interval
        self.data = {
            "current": {},
            "interval": {},
        }
        self.rest_util = RestUtil()
        self.prometheus_util = PrometheusUtil()

    @override
    def update_data(self):
        for metric in self.metrics:
            query_current = metric
            resp = self.prometheus_util.query(query_current)
            self.data["current"][metric] = walk_json(resp, "data", "result")

            query_over_time = "avg_over_time(%s[%s])" % (metric, self.interval)
            resp = self.prometheus_util.query(query_over_time)
            self.data["interval"][metric] = walk_json(resp, "data", "result")

    @override
    def check_health(self, node, stat="interval"):
        return True

    @override
    def prepare(self, node):
        # The default is to wait for jobs to finish on the node
        for job_id, job in node.jobs.items():
            try:
                status = self.rest_util.get_job_status(job_id)["jobStatus"]
                if status in ("running", "scheduling"):
                    return False
            except:
                logger.exception("failed to check job status: %s", job_id)
                return False
        return True

    @override
    def repair(self):
        # The default is to reboot node
        os.system("sync")
        os.system("reboot -f")


@Rule.register_subclass("UnschedulableRule")
class UnschedulableRule(Rule):
    def __init__(self):
        super(UnschedulableRule, self).__init__("unschedulable")

    def update_data(self):
        pass

    def check_health(self, node, stat="interval"):
        if node.unschedulable:
            return False
        else:
            return True


@Rule.register_subclass("ReadyRule")
class ReadyRule(Rule):
    def __init__(self):
        super(ReadyRule, self).__init__("k8s_node_count")

    def check_health(self, node, stat="interval"):
        return True


@Rule.register_subclass("K8sGpuRule")
class K8sGpuRule(Rule):
    def __init__(self):
        super(K8sGpuRule, self).__init__(["k8s_node_gpu_total",
                                          "k8s_node_gpu_allocatable"])

    def get_value(self, node, metric, stat="interval"):
        for item in self.data[stat].get(metric, []):
            if node.ip == item.get("metric", {}).get("host_ip"):
                return item.get("value")
        return None

    def check_health(self, node, stat="interval"):
        try:
            gpu_expected = int(node.gpu_expected)
            gpu_total = self.get_value(node, "k8s_node_gpu_total", stat)
            gpu_allocatable = self.get_value(node, "k8s_node_gpu_allocatable",
                                             stat)
            if gpu_total is None or gpu_allocatable is None:
                return False

            gpu_total = int(gpu_total[1])
            gpu_allocatable = int(gpu_allocatable[1])
            if gpu_expected > gpu_total or gpu_total > gpu_allocatable:
                return False
            return True
        except:
            logger.exception("check health failed")
        return False

    def prepare(self, node):
        # No need to wait for all jobs to finish
        return True

    def repair(self):
        os.system("systemctl restart kubelet")


@Rule.register_subclass("DcgmEccDBERule")
class DcgmEccDBERule(Rule):
    def __init__(self):
        super(DcgmEccDBERule, self).__init__("dcgm_ecc_dbe_volatile_total")

    def get_values(self, node, metric, stat):
        values = []
        for item in self.data[stat].get(metric, []):
            instance = item.get("metric", {}).get("instance")
            instance_ip = instance.split(":")[0]
            if node.ip == instance_ip:
                values.append(int(item.get("value")[1]))
        return values

    def check_health(self, node, stat="interval"):
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
    def __init__(self):
        super(InfinibandRule, self).__init__("infiniband_up")

    def check_health(self, node, stat="interval"):
        try:
            values = self.get_values(node, "infiniband_up", stat)
            for value in values:
                if value > 0:
                    return False
            return True
        except:
            logger.exception("check health failed")
        return False


@Rule.register_subclass("IPoIBRule")
class IPoIBRule(Rule):
    def __init__(self):
        super(IPoIBRule, self).__init__("ipoib_up")

    def check_health(self, node, stat="interval"):
        pass

    def prepare(self, node):
        # No need to wait for all jobs to finish
        return True

    def repair(self):
        os.system("systemctl restart walinuxagent")


@Rule.register_subclass("NvPeerMemRule")
class NvPeerMemRule(Rule):
    def __init__(self):
        super(NvPeerMemRule, self).__init__("nv_peer_mem_count")

    def check_health(self, node, stat="interval"):
        pass

    def prepare(self, node):
        # No need to wait for all jobs to finish
        return True

    def repair(self):
        os.system("systemctl restart nv_peer_mem")


@Rule.register_subclass("NVSMRule")
class NVSMRule(Rule):
    def __init__(self):
        super(NVSMRule, self).__init__(
            ["nvsm_health_total_count", "nvsm_health_good_count"])

    def check_health(self, node, stat="interval"):
        pass

    def repair(self):
        os.environ["TERM"] = "xterm"
        os.system("nvsm dump health")
        os.system("sync")
        os.system("reboot -f")


def instantiate_rules(rule_names):
    if not isinstance(rule_names, list) or len(rule_names) == 0:
        return []
    rules = []
    for rule_name in rule_names:
        if rule_name not in Rule.subclasses:
            logger.warning("rule %s does not have definition", rule_name)
        else:
            rules.append(Rule.subclasses[rule_name]())
    return rules
