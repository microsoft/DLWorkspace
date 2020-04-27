#!/usr/bin/env python3

import urllib.parse
import argparse
import logging
import datetime
import pprint
import sys

import requests

logger = logging.getLogger(__name__)


def walk_json_field_safe(obj, *fields):
    """ for example a=[{"a": {"b": 2}}]
    walk_json_field_safe(a, 0, "a", "b") will get 2
    walk_json_field_safe(a, 0, "not_exist") will get None
    """
    try:
        for f in fields:
            obj = obj[f]
        return obj
    except:
        return None


# capacity, available, unschedulable, used
def get_restful_data(args):
    result = {}
    node_result = {}

    for vc_name in args.vc.split(","):
        query = urllib.parse.urlencode({
            "vcName": vc_name,
            "userName": str(args.alias + "@microsoft.com"),
        })
        url = urllib.parse.urljoin(args.rest_url, "/GetVC") + "?" + query
        body = requests.get(url).json()
        result[vc_name] = {
            "total":
                body["gpu_capacity"].get("P40")
                or body["gpu_capacity"].get("V100"),
            "available":
                body["gpu_avaliable"].get("P40")
                or body["gpu_avaliable"].get("V100"),
            "unschedulable":
                body["gpu_unschedulable"].get("P40")
                or body["gpu_unschedulable"].get("V100"),
        }

        if len(node_result) == 0:
            for node in body["node_status"]:
                node_result[node["InternalIP"]] = {}
                node_result[node["InternalIP"]]["total"] = walk_json_field_safe(
                    node, "gpu_capacity", "P40") or walk_json_field_safe(
                        node, "gpu_capacity", "V100") or 0
                if node["unschedulable"]:
                    node_result[node["InternalIP"]]["allocatable"] = 0
                else:
                    node_result[node["InternalIP"]][
                        "allocatable"] = walk_json_field_safe(
                            node, "gpu_allocatable",
                            "P40") or walk_json_field_safe(
                                node, "gpu_allocatable", "V100") or 0
                node_result[node["InternalIP"]]["used"] = walk_json_field_safe(
                    node, "gpu_used", "P40") or walk_json_field_safe(
                        node, "gpu_used", "V100") or 0
                node_result[node["InternalIP"]][
                    "preemtable_used"] = walk_json_field_safe(
                        node,
                        "gpu_preemptable_used", "P40") or walk_json_field_safe(
                            node, "gpu_preemptable_used", "V100") or 0
    return result, node_result


def get_prometheus_data(args):
    queries = [
        "k8s_vc_gpu_total",
        "k8s_vc_gpu_available",
        "k8s_vc_gpu_unschedulable",
    ]

    result = {}

    for query in queries:
        params = urllib.parse.urlencode({"query": query})

        url = urllib.parse.urljoin(args.prometheus_url,
                                   "/prometheus/api/v1/query") + "?" + params
        body = requests.get(url).json()

        for metric in body["data"]["result"]:
            vc_name = metric["metric"]["vc_name"]
            if vc_name not in result:
                result[vc_name] = {}
            result[vc_name][query] = int(metric["value"][1])

    for vc_name, m in result.items():
        m["total"] = m.pop("k8s_vc_gpu_total")
        m["available"] = m.pop("k8s_vc_gpu_available")
        m["unschedulable"] = m.pop("k8s_vc_gpu_unschedulable")

    node_queries = [
        "k8s_node_gpu_total",
        "k8s_node_gpu_allocatable",
        "k8s_node_gpu_available",
        "k8s_node_preemptable_gpu_available",
    ]
    node_result = {}
    for query in node_queries:
        params = urllib.parse.urlencode({"query": query})

        url = urllib.parse.urljoin(args.prometheus_url,
                                   "/prometheus/api/v1/query") + "?" + params
        body = requests.get(url).json()

        for metric in body["data"]["result"]:
            ip = metric["metric"]["host_ip"]
            if ip not in node_result:
                node_result[ip] = {}
            node_result[ip][query] = int(metric["value"][1])

    for ip, m in node_result.items():
        # total, allocatable, used, preemtable_used,
        m["total"] = m["k8s_node_gpu_total"]
        m["allocatable"] = m["k8s_node_gpu_allocatable"]
        m["used"] = m["k8s_node_gpu_allocatable"] - m["k8s_node_gpu_available"]
        m["preemtable_used"] = m["k8s_node_gpu_available"] - m[
            "k8s_node_preemptable_gpu_available"]

        m.pop("k8s_node_gpu_total")
        m.pop("k8s_node_gpu_allocatable")
        m.pop("k8s_node_gpu_available")
        m.pop("k8s_node_preemptable_gpu_available")

    return result, node_result


def main(args):
    pp = pprint.PrettyPrinter()
    result, node_result = get_restful_data(args)
    presult, p_node_result = get_prometheus_data(args)
    has_diff = False

    if result != presult:
        pp.pprint(result)
        pp.pprint(presult)
        print("-" * 80)
        has_diff = True
    for ip, rest_info in node_result.items():
        p_info = p_node_result[ip]
        if rest_info != p_info:
            print(ip)
            print("restful result")
            pp.pprint(rest_info)
            print("prometheus result")
            pp.pprint(p_info)
            print("-" * 40)
            has_diff = True
    if has_diff:
        sys.exit(1)


if __name__ == "__main__":
    logging.basicConfig(
        format=
        "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)s - %(message)s",
        level=logging.INFO)

    parser = argparse.ArgumentParser(
        description="Check gpu count from prometheus and restfulapi")
    parser.add_argument("--prometheus_url",
                        "-p",
                        default="http://127.0.0.1:9091",
                        help="Prometheus url, eg: http://127.0.0.1:9091")
    parser.add_argument("--rest_url",
                        "-r",
                        default="http://127.0.0.1:5006",
                        help="Restfulapi url, eg: http://127.0.0.1:9091")
    parser.add_argument("--alias",
                        "-a",
                        default="dixu",
                        help="alias to query restfulapi, eg: dixu")
    parser.add_argument("--vc",
                        "-l",
                        default="quantus,relevance2,relevance2inf",
                        help="vc list to query, comma separated")

    args = parser.parse_args()

    main(args)
