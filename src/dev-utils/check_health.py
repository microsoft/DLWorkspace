#!/usr/bin/env python3

import argparse
import base64
import logging
import os
import yaml

from kubernetes import client as k8s_client
from kubernetes.client import Configuration, ApiClient


logger = logging.getLogger(__name__)


def find_infra_node_name(machines):
    for hostname, val in machines.items():
        role_val = val.get("role")
        if type(role_val) == str and role_val == "infrastructure":
            return hostname
        elif type(role_val) == list:
            for role in role_val:
                if role == "infra":
                    return hostname


def get_config(config_path):
    config_path = os.path.join(config_path, "config.yaml")
    with open(config_path) as f:
        config = yaml.full_load(f)
    return config


def build_k8s_config(config_path):
    cluster_path = os.path.join(config_path, "cluster.yaml")
    if not os.path.isfile(cluster_path):
        cluster_path = os.path.join(config_path, "status.yaml")

    with open(cluster_path) as f:
        cluster_config = yaml.full_load(f)

    config = Configuration()

    infra_host = find_infra_node_name(cluster_config["machines"])

    if os.path.isfile(cluster_path):
        config.host = "https://%s.%s:1443" % (
            infra_host, cluster_config["network"]["domain"])
        basic_auth = cluster_config["basic_auth"]
    else:
        config.host = cluster_config["machines"][infra_host]["fqdns"]
        with open(os.path.join(config_path, "clusterID",
                               "k8s_basic_auth.yml")) as auf:
            basic_auth = yaml.safe_load(auf)["basic_auth"]

    config.username = basic_auth.split(",")[1]
    config.password = basic_auth.split(",")[0]
    bearer = "%s:%s" % (config.username, config.password)
    encoded = base64.b64encode(bearer.encode("utf-8")).decode("utf-8")
    config.api_key["authorization"] = "Basic " + encoded

    config.ssl_ca_cert = os.path.join(config_path, "ssl/apiserver/ca.pem")
    return config


def get_k8s_nodes(config_path):
    config = build_k8s_config(config_path)
    api_client = ApiClient(configuration=config)
    k8s_core_api = k8s_client.CoreV1Api(api_client)
    resp = k8s_core_api.list_node()
    return resp.items


def main(args):
    nodes = get_k8s_nodes(args.config)
    for node in nodes:
        for address in node.status.addresses:
            internal_ip = None
            if address.type == 'InternalIP':
                internal_ip = address.address
            hostname = None
            if address.type == 'Hostname':
                hostname = address.address
            logger.info(hostname, internal_ip)


if __name__ == '__main__':
    logging.basicConfig(
        format=
        "%(asctime)s: %(levelname)s - %(filename)s:%(lineno)d@%(process)d: %(message)s",
        level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--config",
                        "-c",
                        required=True,
                        help="path to config dir")
    parser.add_argument("--action",
                        "-a",
                        required=True,
                        help="path to config dir")
    args = parser.parse_args()

    main(args)
