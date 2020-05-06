#!/usr/bin/env python3

import subprocess
import logging
import collections
import time
import datetime
import threading

from prometheus_client.core import GaugeMetricFamily

import utils

logger = logging.getLogger(__name__)


class nv_host(object):
    def __init__(self):
        pass

    def __enter__(self):
        p = subprocess.Popen(["nv-hostengine"],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        code = p.wait(timeout=60)
        logger.info("start nv-hostengine exit with %s, stdout %s, stderr %s",
                    code, p.stdout.read(), p.stderr.read())

    def __exit__(self, type, value, traceback):
        p = subprocess.Popen(["nv-hostengine", "--term"],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        code = p.wait(timeout=60)
        logger.info("stop nv-hostengine exit with %s, stdout %s, stderr %s",
                    code, p.stdout.read(), p.stderr.read())


# Ref: https://github.com/NVIDIA/gpu-monitoring-tools/blob/9e2979804d297cf5a81640ba8a8e941365e58f14/dcgm-exporter/dcgm-exporter#L85
mapping = [
    (54, "uuid",
     "uuid of gpu"), # do not remove uuid, this is very important label
    (100, "sm_clock", "SM clock frequency (in MHz)."),
    (101, "memory_clock", "Memory clock frequency (in MHz)."),
    (140, "memory_temp", "Memory temperature (in C)."),
    (150, "gpu_temp", "GPU temperature (in C)."),
    (155, "power_usage", "Power draw (in W)."),
    (156, "total_energy_consumption",
     "Total energy consumption since boot (in mJ)."),
    (200, "pcie_tx_throughput",
     "Total number of bytes transmitted through PCIe TX (in KB) via NVML."),
    (201, "pcie_rx_throughput",
     "Total number of bytes received through PCIe RX (in KB) via NVML."),
    (202, "pcie_replay_counter", "Total number of PCIe retries."),
    (203, "gpu_util", "GPU utilization (in %)."),
    (204, "mem_copy_util", "Memory utilization (in %)."),
    (206, "enc_util", "Encoder utilization (in %)."),
    (207, "dec_util", "Decoder utilization (in %)."),
    (230, "xid_errors", "Value of the last XID error encountered."),
    (240, "power_violation",
     "Throttling duration due to power constraints (in us)."),
    (241, "thermal_violation",
     "Throttling duration due to thermal constraints (in us)."),
    (242, "sync_boost_violation",
     "Throttling duration due to sync-boost constraints (in us)."),
    (243, "board_limit_violation",
     "Throttling duration due to board limit constraints (in us)."),
    (244, "low_util_violation",
     "Throttling duration due to low utilization (in us)."),
    (245, "reliability_violation",
     "Throttling duration due to reliability constraints (in us)."),
    (246, "app_clock_violation", "Total throttling duration (in us)."),
    (251, "fb_free", "Framebuffer memory free (in MiB)."),
    (252, "fb_used", "Framebuffer memory used (in MiB)."),
    (310, "ecc_sbe_volatile_total",
     "Total number of single-bit volatile ECC errors."),
    (311, "ecc_dbe_volatile_total",
     "Total number of double-bit volatile ECC errors."),
    (312, "ecc_sbe_aggregate_total",
     "Total number of single-bit persistent ECC errors."),
    (313, "ecc_dbe_aggregate_total",
     "Total number of double-bit persistent ECC errors."),
    (390, "retired_pages_sbe",
     "Total number of retired pages due to single-bit errors."),
    (391, "retired_pages_dbe",
     "Total number of retired pages due to double-bit errors."),
    (392, "retired_pages_pending", "Total number of pages pending retirement."),
    (409, "nvlink_flit_crc_error_count_total",
     "Total number of NVLink flow-control CRC errors."),
    (419, "nvlink_data_crc_error_count_total",
     "Total number of NVLink data CRC errors."),
    (429, "nvlink_replay_error_count_total", "Total number of NVLink retries."),
    (439, "nvlink_recovery_error_count_total",
     "Total number of NVLink recovery errors."),
    (449, "nvlink_bandwidth_total",
     "Total number of NVLink bandwidth counters for all lanes"),
]

DCGMMetrics = collections.namedtuple("DCGMMetrics",
                                     list(map(lambda x: x[1], mapping)))


class DCGMHandler(object):
    def __init__(self, interval, gauge_ref, info_ref, dcgmi_histogram,
                 dcgmi_timeout):
        self.interval = interval
        self.gauge_ref = gauge_ref
        self.info_ref = info_ref
        self.dcgmi_histogram = dcgmi_histogram
        self.dcgmi_timeout = dcgmi_timeout

        self.args = ",".join(map(lambda x: str(x[0]), mapping))
        self.thread = None

    def start(self):
        self.thread = threading.Thread(target=self.run,
                                       name="dcgm_handler",
                                       args=(),
                                       daemon=True)
        self.thread.start()

    def run(self):
        with nv_host():
            while True:
                try:
                    metrics, gauges = self.get_dcgm_metric()
                    now = datetime.datetime.now()
                    self.info_ref.set(metrics, now)
                    self.gauge_ref.set(gauges, now)
                    time.sleep(self.interval)
                except Exception:
                    logger.exception("DCGMHandler.run got exception")

    def get_dcgm_metric(self):
        metrics = {} # minor_number -> DCGMMetrics
        gauges = {} # gauge_name -> GaugeMetricFamily

        try:
            dcgmi_output = utils.exec_cmd(
                ["dcgmi", "dmon", "-c", "1", "-d", "1", "-e", self.args],
                histogram=self.dcgmi_histogram,
                timeout=self.dcgmi_timeout)
        except subprocess.CalledProcessError as e:
            logger.exception("command '%s' return with error (code %d): %s",
                             e.cmd, e.returncode, e.output)
            return metrics, gauges
        except subprocess.TimeoutExpired:
            logger.warning("dcgmi timeout")
            return metrics, gauges

        try:
            for _, name, desc in mapping[1:]:
                gauges[name] = GaugeMetricFamily(
                    "dcgm_" + name, desc, labels=["minor_number", "uuid"])

            # [2:] is to remove headers
            for line in dcgmi_output.split("\n")[2:]:
                if line == "": # end of output
                    continue
                part = line.split()
                minor_number = part[0]

                args = {}
                for i, (_, name, _) in enumerate(mapping):
                    value = part[i + 1]
                    args[name] = value
                    if name == "uuid": # do not generate uuid metric
                        continue
                    if value == "N/A":
                        continue
                    args[name] = float(value)

                    gauges[name].add_metric([minor_number, args["uuid"]],
                                            float(value))

                metrics[minor_number] = DCGMMetrics(**args)
            return metrics, gauges
        except Exception:
            logger.exception("calling dcgmi failed")
            return metrics, gauges


if __name__ == '__main__':
    logging.basicConfig(
        format=
        "%(asctime)s - %(levelname)s - %(threadName)s - %(filename)s:%(lineno)s - %(message)s",
        level="DEBUG")

    import collector
    import datetime

    from prometheus_client import Histogram

    cmd_histogram = Histogram("cmd_dcgmi_latency_seconds",
                              "Command call latency for nvidia-smi (seconds)",
                              buckets=(1.0, 2.0, 4.0, 8.0, 16.0, 32.0,
                                       64.0, 128.0, 256.0, 512.0, 1024.0,
                                       float("inf")))

    gauge_ref = collector.AtomicRef(datetime.timedelta(seconds=60))
    metric_ref = collector.AtomicRef(datetime.timedelta(seconds=60))

    dcgm_handler = dcgm.DCGMHandler(1, self.gauge_ref, metric_ref,
                                    cmd_histogram, 600)
    dcgm_handler.run()

    for _ in range(10):
        now = datetime.datetime.now()

        gauge = gauge_ref.get(now)
        metric = metric_ref.get(now)

        logger.info("gauge is %s", gauge)
        logger.info("metric is %s", metric)
        time.sleep(2)
