#!/usr/bin/env python3

import datetime
import glob
import os
import re
import logging
import subprocess
import threading
import time

import utils
import network

from prometheus_client.core import GaugeMetricFamily

logger = logging.getLogger(__name__)

HOST_FS = "/host-fs"
INFINIBAND_PATH = os.path.join(HOST_FS, "sys/class/infiniband")


def first_line(filepath):
    """Get the first line of the path content. No exception handling"""
    with open(filepath) as f:
        content = f.readlines()
    return content[0].strip()


class Infiniband(object):
    label_names = [
        "device", "port", "link_layer", "rate", "state", "phys_state"
    ]

    def __init__(self, device, port, link_layer, rate, state, phys_state,
                 receive_bytes, transmit_bytes):
        self.device = device
        self.port = port
        self.link_layer = link_layer
        self.rate = rate
        self.state = state
        self.phys_state = phys_state
        self.receive_bytes = receive_bytes
        self.transmit_bytes = transmit_bytes

    @property
    def labels(self):
        return {
            label_name: self.__dict__[label_name]
            for label_name in Infiniband.label_names
        }

    def __repr__(self):
        return str(self.__dict__)


def get_infinibands():
    paths = glob.glob(os.path.join(INFINIBAND_PATH, "*/ports/*"))
    infinibands = []
    for path in paths:
        try:
            # device and port must exist for an Infiniband port. E.g.
            # /host-fs/sys/class/infiniband/mlx4_0/ports/1 has
            # - device: mlx4_0
            # - port: 1
            device_pattern = re.compile("/infiniband/.+/ports/")
            matches = re.findall(device_pattern, path)
            if len(matches) == 0:
                continue
            else:
                device = matches[0].split("/")[2]

            port_pattern = re.compile("/ports/[0-9]+$")
            matches = re.findall(port_pattern, path)
            if len(matches) == 0:
                continue
            else:
                port = matches[0].split("/")[2]

            # link_layer, rate, state, phys_state must exist
            link_layer = first_line(os.path.join(path, "link_layer"))
            rate = first_line(os.path.join(path, "rate"))
            state = first_line(
                os.path.join(path, "state")).split(":")[-1].strip()
            phys_state = first_line(
                os.path.join(path, "phys_state")).split(":")[-1].strip()

            # /host-fs/sys/class/infiniband/*/ports/*/counters/* cannot be
            # read if Mellanox LNX OFED driver is not installed. We will ignore
            # collecting rcv and xmit metric data in this case.
            # Example error:
            #   ~$ cat /sys/class/infiniband/mlx4_0/ports/1/counters/port_rcv_data
            #   cat: /sys/class/infiniband/mlx4_0/ports/1/counters/port_rcv_data: Invalid argument
            # To prevent
            try:
                # Ref https://github.com/prometheus/node_exporter/pull/579/files
                # According to Mellanox, the following metrics "are divided by
                # 4 unconditionally" as they represent the amount of data being
                # transmitted and received per lane. Mellanox cards have 4
                # lanes per port, so all values must be multiplied by 4 to get
                # the expected value.
                receive_bytes = 4 * int(
                    first_line(os.path.join(path, "counters", "port_rcv_data")))
                transmit_bytes = 4 * int(
                    first_line(os.path.join(path, "counters",
                                            "port_xmit_data")))
            except Exception as e:
                logger.debug("Failed to parse rcv/xmit metric data. %s", e)
                receive_bytes = None
                transmit_bytes = None

            infiniband = Infiniband(device, port, link_layer, rate, state,
                                    phys_state, receive_bytes, transmit_bytes)
            infinibands.append(infiniband)
        except:
            logger.exception("failed to parse infiniband at %s", path)
    return infinibands


class InfinibandHandler(object):
    def __init__(self, interval, gauge_ref, info_ref):
        self.interval = interval
        self.gauge_ref = gauge_ref
        self.info_ref = info_ref
        self.thread = None

    def start(self):
        self.thread = threading.Thread(target=self.run,
                                       name="infiniband_handler",
                                       args=(),
                                       daemon=True)
        self.thread.start()

    def run(self):
        while True:
            try:
                metric, gauge = self.get_infiniband_metric()
                now = datetime.datetime.now()
                self.info_ref.set(metric, now)
                self.gauge_ref.set(gauge, now)
                time.sleep(self.interval)
            except:
                logger.exception("InfinibandHandler.run got exception")

    def get_infiniband_metric(self):
        gauge = GaugeMetricFamily("infiniband_up",
                                  "Whether infiniband is up",
                                  labels=Infiniband.label_names)
        metric = [] # A list of Infiniband

        try:
            infinibands = get_infinibands()
            for infiniband in infinibands:
                if infiniband.state == "ACTIVE" and \
                        infiniband.phys_state == "LinkUp":
                    value = 1
                else:
                    value = 0
                gauge.add_metric(list(infiniband.labels.values()), value)
                metric.append(infiniband)
            return metric, gauge
        except:
            logger.exception("getting infiniband metric failed")
            return metric, gauge


class IPoIBInterface(object):
    label_names = ["device", "state"]

    def __init__(self, device, state, receive_bytes, transmit_bytes):
        self.device = device
        self.state = state
        self.receive_bytes = receive_bytes
        self.transmit_bytes = transmit_bytes

    @property
    def labels(self):
        return {
            label_name: self.__dict__[label_name]
            for label_name in IPoIBInterface.label_names
        }

    def __repr__(self):
        return str(self.__dict__)


def get_all_ipoib_and_state():
    cmd = ["chroot", HOST_FS, "ip", "link", "show"]
    try:
        output = utils.exec_cmd(cmd, timeout=3)
    except subprocess.TimeoutExpired:
        logger.warning("%s timeout", " ".join(cmd))
        return []
    except:
        logger.exception("failed to execute %s", " ".join(cmd))
        return []

    ipoibs = []
    pattern = re.compile("^[0-9]+:[ ]*ib[0-9]+:")
    for line in output.split("\n"):
        if re.match(pattern, line):
            try:
                device = line.split(":")[1].strip()
                state = line.split(":")[-1].strip().split()[6]
                ipoibs.append((device, state))
            except:
                logger.warning("failed to parse ipoib from %s", line)

    return ipoibs


def get_ipoib_interfaces():
    ipoib_interfaces = []
    for device, state in get_all_ipoib_and_state():
        try:
            receive_bytes, transmit_bytes = \
                network.get_network_consumption(device)
            ipoib_interface = IPoIBInterface(device, state, receive_bytes,
                                             transmit_bytes)
            ipoib_interfaces.append(ipoib_interface)
        except:
            logger.exception("failed to get ipoib interfaces")
    return ipoib_interfaces


class IPoIBHandler(object):
    def __init__(self, interval, gauge_ref, info_ref):
        self.interval = interval
        self.gauge_ref = gauge_ref
        self.info_ref = info_ref
        self.thread = None

    def start(self):
        self.thread = threading.Thread(target=self.run,
                                       name="ipoib_handler",
                                       args=(),
                                       daemon=True)
        self.thread.start()

    def run(self):
        while True:
            try:
                metric, gauge = self.get_ipoib_metric()
                now = datetime.datetime.now()
                self.info_ref.set(metric, now)
                self.gauge_ref.set(gauge, now)
                time.sleep(self.interval)
            except:
                logger.exception("IPoIBHandler.run got exception")

    def get_ipoib_metric(self):
        gauge = GaugeMetricFamily("ipoib_up",
                                  "Whether ipoib interface is up",
                                  labels=IPoIBInterface.label_names)
        metric = [] # A list of IPoIBInterface

        try:
            ipoib_interfaces = get_ipoib_interfaces()
            for ipoib_interface in ipoib_interfaces:
                if ipoib_interface.state == "UP":
                    value = 1
                else:
                    value = 0
                gauge.add_metric(list(ipoib_interface.labels.values()), value)
                metric.append(ipoib_interface)
            return metric, gauge
        except:
            logger.exception("getting ipoib metric failed")
            return metric, gauge


if __name__ == '__main__':
    logging.basicConfig(
        format=
        "%(asctime)s - %(levelname)s - %(threadName)s - %(filename)s:%(lineno)s - %(message)s",
        level="DEBUG")

    import collector
    import datetime

    infiniband_gauge_ref = collector.AtomicRef(datetime.timedelta(seconds=60))
    infiniband_metric_ref = collector.AtomicRef(datetime.timedelta(seconds=60))

    infiniband_handler = InfinibandHandler(1, infiniband_gauge_ref,
                                           infiniband_metric_ref)
    infiniband_handler.start()

    ipoib_gauge_ref = collector.AtomicRef(datetime.timedelta(seconds=60))
    ipoib_metric_ref = collector.AtomicRef(datetime.timedelta(seconds=60))

    ipoib_handler = IPoIBHandler(1, ipoib_gauge_ref, ipoib_metric_ref)
    ipoib_handler.start()

    for _ in range(10):
        now = datetime.datetime.now()

        infiniband_gauge = infiniband_gauge_ref.get(now)
        infiniband_metric = infiniband_metric_ref.get(now)
        ipoib_gauge = ipoib_gauge_ref.get(now)
        ipoib_metric = ipoib_metric_ref.get(now)

        logger.info("infiniband gauge is %s", infiniband_gauge)
        logger.info("infiniband metric is %s", infiniband_metric)
        logger.info("ipoib gauge is %s", ipoib_gauge)
        logger.info("ipoib metric is %s", ipoib_metric)
        time.sleep(2)

