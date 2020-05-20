#!/usr/bin/env python3

import re
import logging
import collections
import subprocess

import utils

from prometheus_client.core import GaugeMetricFamily

logger = logging.getLogger(__name__)

HOST_FS = "/host-fs"

# Ref https://github.com/HewlettPackard/lustre_exporter
# We choose to implement our own metrics collection because
# 1. Some important metrics (e.g. storage usage) are somehow not retrieved
#    when deploying the lustre_exporter as a docker container
# 2. lustre_exporter parses files instead of using lctl. According to
#    http://wiki.lustre.org/Lustre_Monitoring_and_Statistics_Guide, we should
#    use lctl command line to insure portability.

# (metric name, param pattern, description)
# health_check exists on client nodes as well.
health_metrics = [
    ("health_check", "health_check", "Current health status for the indicated instance"),
]


mdt_metrics = [
    ("stats_total", "mdt.*.md_stats", "Number of operations the filesystem has performed."),
    ("inodes_free", "osd-*.*.filesfree", "The number of inodes (objects) available"),
    ("inodes_maximum", "osd-*.*.filestotal", "The maximum number of inodes (objects) the filesystem can hold"),
    ("capacity_kilobytes", "osd-*.*.kbytestotal", "Capacity of the pool in kilobytes"),
    ("free_kilobytes", "osd-*.*.kbytesfree", "Number of kilobytes allocated to the pool"),
    ("available_kilobytes", "osd-*.*.kbytesavail", "Number of kilobytes readily available in the pool"),
    ("num_exports", "mdt.*.num_exports", "Total number of times the pool has been exported"),
]


ost_metrics = [
    ("stats_total", "obdfilter.*.stats", "Number of operations the filesystem has performed."),
    ("read_samples_total", "obdfilter.*.stats", "Total number of reads that have been recorded."),
    ("read_bytes_minimum", "obdfilter.*.stats", "The minimum read size in bytes."),
    ("read_bytes_maximum", "obdfilter.*.stats", "The maximum read size in bytes."),
    ("read_bytes_total", "obdfilter.*.stats", "The total number of bytes that have been read."),
    ("write_samples_total", "obdfilter.*.stats", "Total number of writes that have been recorded."),
    ("write_bytes_minimum", "obdfilter.*.stats", "The minimum write size in bytes."),
    ("write_bytes_maximum", "obdfilter.*.stats", "The maximum write size in bytes."),
    ("write_bytes_total", "obdfilter.*.stats", "The total number of bytes that have been written."),
    ("inodes_free", "obdfilter.*.filesfree", "The number of inodes (objects) available"),
    ("inodes_maximum", "obdfilter.*.filestotal", "The maximum number of inodes (objects) the filesystem can hold"),
    ("capacity_kilobytes", "obdfilter.*.kbytestotal", "Capacity of the pool in kilobytes"),
    ("free_kilobytes", "obdfilter.*.kbytesfree", "Number of kilobytes allocated to the pool"),
    ("available_kilobytes", "obdfilter.*.kbytesavail", "Number of kilobytes readily available in the pool"),
    ("num_exports", "obdfilter.*.num_exports", "Total number of times the pool has been exported"),
]


metric_mapping = {
    "health": health_metrics,
    "mdt": mdt_metrics,
    "ost": ost_metrics,
}


metric_val_string_to_num = {
    "healthy": 1,
    "unhealthy": 0
}


# stats metric -> (operation, regex group index)
# This is used to construct regex to get values
stats_regex_group_indices = {
    "stats_total": [
        ("open", 0),
        ("close", 0),
        ("mknod", 0),
        ("link", 0),
        ("unlink", 0),
        ("mkdir", 0),
        ("rmdir", 0),
        ("rename", 0),
        ("getattr", 0),
        ("setattr", 0),
        ("getxattr", 0),
        ("setxattr", 0),
        ("statfs", 0),
        ("sync", 0),
        ("samedir_rename", 0),
        ("crossdir_rename", 0),
        ("punch", 0),
        ("destroy", 0),
        ("create", 0),
        ("get_info", 0),
        ("set_info", 0),
    ],
    "read_samples_total": ("read_bytes", 0),
    "read_bytes_minimum": ("read_bytes", 1),
    "read_bytes_maximum": ("read_bytes", 2),
    "read_bytes_total": ("read_bytes", 3),
    "write_samples_total": ("write_bytes", 0),
    "write_bytes_minimum": ("write_bytes", 1),
    "write_bytes_maximum": ("write_bytes", 2),
    "write_bytes_total": ("write_bytes", 3),
}


class LustreMetric(object):
    def __init__(self, name, pattern, desc, server, role):
        self.name = name
        self.pattern = pattern
        self.desc = desc
        self.server = server
        self.role = role

    def __repr__(self):
        return str(self.__dict__)


def gen_lustre_gauge(lmetric, labels):
    return GaugeMetricFamily("lustre_" + lmetric.name, lmetric.desc,
                             labels=labels)


def lctl_get_param(pattern):
    cmd = None
    try:
        cmd = ["chroot", HOST_FS, "lctl", "get_param", pattern]
        return utils.exec_cmd(cmd, stderr=subprocess.STDOUT, timeout=3)
    except subprocess.TimeoutExpired as e:
        logger.debug("%s timeout", cmd)
    except subprocess.CalledProcessError as e:
        if e.returncode == 127:
            raise e  # Signal LustreCollector to reset sleep time to 1 day
        else:
            logger.debug("%s returns %d, output %s", cmd, e.returncode,
                         e.output)
    except:
        logger.debug("%s failed", cmd)
    return None


def get_server():
    if lctl_get_param("mds.MDS.uuid"):
        return "mds"
    elif lctl_get_param("ost.OSS.uuid"):
        return "oss"
    else:
        return "client"


def group_content(content):
    # Contents look like
    # 1.
    # obdfilter.lustrefs-OST0001.stats=
    # snapshot_time             1589587093.814210648 secs.nsecs
    # read_bytes                69863 samples [bytes] 4096 4194304 109618311168
    # write_bytes               215725 samples [bytes] 8 4194304 899120050824
    # setattr                   5 samples [reqs]
    # punch                     6 samples [reqs]
    # sync                      119 samples [reqs]
    # destroy                   2499452 samples [reqs]
    # create                    945 samples [reqs]
    # statfs                    49393 samples [reqs]
    # get_info                  1 samples [reqs]
    # set_info                  66 samples [reqs]
    # obdfilter.lustrefs-OST0002.stats=
    # snapshot_time             1589587093.814285550 secs.nsecs
    # read_bytes                28566 samples [bytes] 4096 4194304 104786370560
    # write_bytes               214432 samples [bytes] 8 4194304 898702186809
    # setattr                   8 samples [reqs]
    # punch                     24 samples [reqs]
    # sync                      119 samples [reqs]
    # destroy                   2499551 samples [reqs]
    # create                    919 samples [reqs]
    # statfs                    49389 samples [reqs]
    # get_info                  1 samples [reqs]
    # set_info                  60 samples [reqs]
    # ...
    #
    # 2.
    # health_check=healthy
    # TODO: Find the proper regex to do this.
    groups = collections.defaultdict(lambda: [])
    key = None
    for line in content.splitlines():
        match = re.match(r"(^[\S]+)=", line)
        if match is not None:
            key = match.groups()[0]
        if key is None:
            continue
        groups[key].append(line)
    ret = {key: "\n".join(lines) for key, lines in groups.items()}
    return ret


def get_component_and_target(key):
    key_splits = key.split(".")
    if len(key_splits) >= 2:
        component = key_splits[0]
        target = key_splits[1]
    else:
        component = target = "N/A"
    return component, target


def parse_single_metrics(content, lmetric):
    labels = ["server", "role", "component", "target"]
    gauge = gen_lustre_gauge(lmetric, labels=labels)

    for key, data in content.items():
        try:
            value_str = data.split("=")[-1]
            try:
                value = int(value_str)
            except:
                value = metric_val_string_to_num.get(value_str)
            if value is None:
                continue
            component, target = get_component_and_target(key)
            gauge.add_metric(
                [lmetric.server, lmetric.role, component, target], value)
        except:
            logger.debug("parsing key %s data %s failed", key, data)
    return gauge


def parse_stats_metrics(content, lmetric):
    labels = ["server", "role", "component", "target", "operation"]
    gauge = gen_lustre_gauge(lmetric, labels=labels)

    metric_regex_group_indices = stats_regex_group_indices[lmetric.name]
    if not isinstance(metric_regex_group_indices, list):
        metric_regex_group_indices = [metric_regex_group_indices]

    for key, data in content.items():
        for metric_regex_group_index in metric_regex_group_indices:
            try:
                op = metric_regex_group_index[0]
                index = metric_regex_group_index[1]
                regex = re.compile(
                    r"%s\s+(\d+) samples \[\w+\]\s*(\d*)\s*(\d*)\s*(\d*)" % op)

                match = regex.findall(data)
                if len(match) != 1:
                    continue
                value = int(match[0][index])
                component, target = get_component_and_target(key)
                gauge.add_metric([lmetric.server, lmetric.role, component,
                                  target, op], value)
            except:
                logger.debug("parsing key %s data %s failed", key, data)
    return gauge


def parse_lmetric(content, lmetric):
    if content is None:
        return None

    content = group_content(content)

    if not lmetric.pattern.endswith("stats"):
        return parse_single_metrics(content, lmetric)
    else:
        return parse_stats_metrics(content, lmetric)


def get_lustre_gauges():
    gauges = []

    # Get server (mds, oss, or client)
    server = get_server()

    lustre_metrics = []
    for role, metric_tuples in metric_mapping.items():
        for name, pattern, desc in metric_tuples:
            lustre_metrics.append(
                LustreMetric(name, pattern, desc, server, role))

    # Different metrics can be derived from the same lctl param pattern call
    # pattern -> [metric]
    pattern_to_lmetrics = collections.defaultdict(lambda: [])
    for lmetric in lustre_metrics:
        pattern_to_lmetrics[lmetric.pattern].append(lmetric)

    # Parse metrics fro each lctl param pattern call
    for pattern, lmetrics in pattern_to_lmetrics.items():
        content = lctl_get_param(pattern)
        for lmetric in lmetrics:
            gauge = parse_lmetric(content, lmetric)
            if gauge:
                gauges.append(gauge)

    return gauges


if __name__ == '__main__':
    logging.basicConfig(
        format= "%(asctime)s - %(levelname)s - %(threadName)s - %(filename)s:%(lineno)s - %(message)s",
        level="DEBUG")

    try:
        lustre_gauges = get_lustre_gauges()
        print(lustre_gauges)
    except subprocess.CalledProcessError as e:
        if e.returncode == 127:
            logger.info("lctl is not installed")
    except:
        logger.exception("failed to collect lustre metrics")
