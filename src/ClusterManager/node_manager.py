#!/usr/bin/env python3

import json
import os
import time
import argparse
import sys
import yaml
import logging
import logging.config
import copy
import datetime

sys.path.append(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "../utils"))

from cluster_manager import setup_exporter_thread, \
    manager_iteration_histogram, register_stack_trace_dump, \
    update_file_modification_time, AtomicRef
from DataHandler import DataHandler
from config import config

import k8s_utils

from cluster_status import ClusterStatusFactory
from virtual_cluster_status import VirtualClusterStatusesFactory

k8s = k8s_utils.K8sUtil()

logger = logging.getLogger(__name__)


def create_log(logdir='/var/log/dlworkspace'):
    if not os.path.exists(logdir):
        os.system("mkdir -p " + logdir)
    with open('logging.yaml') as f:
        logging_config = yaml.full_load(f)
        f.close()
        logging_config["handlers"]["file"]["filename"] = logdir + \
            "/nodemanager.log"
        logging.config.dictConfig(logging_config)


def get_cluster_status():
    """Update in DB and returns cluster status.

    Returns:
        A dictionary representing cluster status.
    """
    cluster_status = {}
    metrics = []

    try:
        with DataHandler() as data_handler:
            vc_list = data_handler.ListVCs()
            jobs = data_handler.GetActiveJobList()

        # Set up cluster status
        nodes = k8s.get_all_nodes()
        pods = k8s.get_all_pods()
        prometheus_node = config.get("prometheus_node", "127.0.0.1")
        cs_factory = ClusterStatusFactory(prometheus_node, nodes, pods, jobs)
        cs = cs_factory.make()
        cluster_status = cs.to_dict()

        # TODO: Deprecate typo "gpu_avaliable" in legacy code
        cluster_status["gpu_avaliable"] = cluster_status["gpu_available"]

        # TODO: Deprecate typo "AvaliableJobNum" in legacy code
        cluster_status["AvaliableJobNum"] = cluster_status["available_job_num"]

        # Set up virtual cluster views
        vc_statuses_factory = VirtualClusterStatusesFactory(cs, vc_list)
        vc_statuses = vc_statuses_factory.make()
        vc_statuses_dict = {
            vc_name: vc_status.to_dict()
            for vc_name, vc_status in vc_statuses.items()
        }
        for _, vc_status in vc_statuses.items():
            result = vc_status.to_metrics()
            metrics.extend(result)

        cluster_status["vc_statuses"] = vc_statuses_dict
    except:
        logger.exception("Exception in setting up cluster status")

    try:
        if "cluster_status" in config and \
                config["cluster_status"] != cluster_status:
            size = len(json.dumps(cluster_status, separators=(",", ":")))
            logger.info("updating the cluster status (of len %s)...", size)
            with DataHandler() as data_handler:
                data_handler.UpdateClusterStatus(cluster_status)
        else:
            logger.info("No diff in cluster status, skipping update in DB...")
    except:
        logger.exception("Error in updating cluster status")

    config["cluster_status"] = copy.deepcopy(cluster_status)
    return metrics


def run(args):
    register_stack_trace_dump()
    create_log()

    decay_time = datetime.timedelta(seconds=0) # do not retire old data
    atomic_ref = AtomicRef(decay_time)

    setup_exporter_thread(args.port, refs=[atomic_ref])

    logger.info("start to update nodes usage information ...")
    config["cluster_status"] = None

    while True:
        update_file_modification_time("node_manager")

        with manager_iteration_histogram.labels("node_manager").time():
            try:
                metrics = get_cluster_status()
                atomic_ref.set(metrics, datetime.datetime.now())
            except:
                logger.exception("get cluster status failed")
        time.sleep(10)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--port",
                        "-p",
                        help="port of exporter",
                        type=int,
                        default=9202)
    args = parser.parse_args()

    run(args)
