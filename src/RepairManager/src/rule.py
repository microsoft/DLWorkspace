#!/usr/bin/env python3

from util import PrometheusUtil, walk_json


def override(func):
    return func


class Rule(object):
    def __init__(self, metric):
        self.metric = metric
        self.query = None
        self.metric_data = None
        self.prometheus_util = PrometheusUtil()

    def get_metric_data(self):
        resp = self.prometheus_util.query(query=self.query)
        self.metric_data = walk_json(resp, "data", "result")

    @override
    def check(self, node):
        pass

    @override
    def prepare(self, node):
        pass

    @override
    def repair(self, node):
        pass


class GpuCapacityRule(Rule):
    def __init__(self):
        pass


class GpuAllocatableRule(Rule):
    def __init__(self):
        pass


class DcgmDBERule(Rule):
    def __init__(self):
        query = "avg_over_time(dcgm_ecc_dbe_volatile_total[5m])>0"
        super(DcgmDBERule, self).__init__(query=query)


class InfinibandRule(Rule):
    def __init__(self):
        pass


class IPoIBRule(Rule):
    def __init__(self):
        pass


class NvPeerMemRule(Rule):
    def __init__(self):
        pass


class NVSMRule(Rule):
    def __init__(self):
        pass