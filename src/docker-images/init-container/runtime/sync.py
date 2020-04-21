#!/usr/bin/env python3

import os
import sys
import argparse
import logging
import socket
from contextlib import closing
import json
import time
import random
from pathlib import Path
import re

from kubernetes import client as k8s_client
from kubernetes import config as k8s_config
from kubernetes.client.rest import ApiException

logger = logging.getLogger(__name__)

job_namespace = "default"

ERROR_EXIT_CODE = {
    "environment": 200,
    "network": 201,
    "k8s_api": 202,
    "port": 203,
    "wait_sync_fail": 204,
}


def find_free_port(min=40000, max=49999):
    for i in range(100): # try 100 times
        port = random.randint(min, max)

        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            try:
                s.bind(("", port))
            except OSError:
                if i > 10:
                    logger.warning("failed %d times to get free port", i)
                continue
            return port

    logger.error("failed to get free port")
    sys.exit(ERROR_EXIT_CODE["port"])


def get_pod_name():
    return os.environ.get("POD_NAME")


def get_job_name():
    return os.environ.get("DLTS_JOB_ID")


def get_pod_ip():
    return os.environ.get("POD_IP")


def get_ps_number():
    return int(os.environ.get("DLTS_NUM_PS", 0))


def get_worker_number():
    return int(os.environ.get("DLTS_NUM_WORKER", 0))


def get_framework_attempt_id():
    return os.environ.get("FC_FRAMEWORK_ATTEMPT_ID", "0")


def get_task_attempt_id():
    return os.environ.get("FC_TASK_ATTEMPT_ID", "0")


def create_own_config(k8s_core_api, job_name, pod_name, ip, ssh_port,
                      framework_attempt, task_attempt):
    config_name = "c-" + pod_name

    labels = {
        "run": job_name,
        "framework_attempt_id": framework_attempt,
        "task_attempt_id": task_attempt
    }

    metadata = k8s_client.V1ObjectMeta(
        namespace=job_namespace,
        name=config_name,
        labels=labels,
    )

    data = json.dumps({"ip": ip, "ssh_port": ssh_port})

    body = k8s_client.V1ConfigMap(data={"pod.json": data}, metadata=metadata)

    for i in range(2):
        try:
            resp = k8s_core_api.create_namespaced_config_map(
                namespace=job_namespace,
                body=body,
            )
            logger.debug("created configmap %s, resp is %s", config_name, resp)
        except ApiException as e:
            if e.status == 409:
                logger.info(
                    "configmap already exist, maybe from previous retry, delete it, retry %d",
                    i)
                try:
                    api_response = k8s_core_api.delete_namespaced_config_map(
                        config_name,
                        job_namespace,
                    )
                except ApiException as e:
                    logger.warning("delete configmap failed", exc_info=True)
                continue
            else:
                logger.exception("create configmap with data %s failed", data)
                sys.exit(ERROR_EXIT_CODE["k8s_api"])
        except Exception as e:
            logger.exception("create configmap with data %s failed", data)
            sys.exit(ERROR_EXIT_CODE["network"])
        return config_name
    sys.exit(ERROR_EXIT_CODE["k8s_api"])


def export_env(path, envs):
    with open(path, "w") as f:
        for k, v in envs.items():
            f.write("export %s=%s\n" % (k, v))


def get_role_idx():
    inferred = os.environ["POD_NAME"].split("-")[-1]
    if inferred.isdigit():
        return inferred
    match = re.match("([a-z]+)([0-9]+)", inferred)
    if match:
        role, idx = match.groups()
        return idx
    else:
        logger.error("could not get role index from environ %s, assume 0",
                     os.environ)
        return "0"


def main(args):
    pod_name = get_pod_name()
    job_name = get_job_name()
    ip = get_pod_ip()
    self_role_idx = get_role_idx()

    if os.environ.get("DLTS_HOST_NETWORK") == "enable":
        ssh_port = find_free_port()
    else:
        ssh_port = 22

    ps_num = get_ps_number()
    worker_num = get_worker_number()
    expected_num = ps_num + worker_num

    framework_attempt = get_framework_attempt_id()
    task_attempt = get_task_attempt_id()

    logger.debug(
        "pod_name %s, job_name %s, ip %s, port %d, ps_num %d, worker_num %d, framework_attempt %s, task_attempt %s",
        pod_name, job_name, ip, ssh_port, ps_num, worker_num, framework_attempt,
        task_attempt)

    if pod_name is None or job_name is None or ip is None:
        logger.error("one of essential environment variable is missing %s", {
            "pod_name": pod_name,
            "job_name": job_name,
            "ip": ip
        })
        sys.exit(ERROR_EXIT_CODE["environment"])

    # SD stands for service discovery
    envs = {
        "DLTS_SD_SELF_IP": ip,
        "DLTS_SD_SELF_SSH_PORT": ssh_port,
        "DLWS_ROLE_IDX": self_role_idx,
        "DLTS_ROLE_IDX": self_role_idx,
    }

    if expected_num == 1:
        logger.info("do not need to sync, skip")
    else:
        k8s_config.load_incluster_config()
        k8s_core_api = k8s_client.CoreV1Api()
        # k8s_apps_api = k8s_client.AppsV1Api()

        config_name = create_own_config(k8s_core_api, job_name, pod_name, ip,
                                        ssh_port, framework_attempt,
                                        task_attempt)

        labels = "run=%s,framework_attempt_id=%s,task_attempt_id=%s" % (
            job_name, framework_attempt, task_attempt)

        items = []
        # wait forever. If the resource is not enought, some worker will be in pending state, if
        # we exit the job will fail, and user will be confused. Although this wastes some resource
        # already allocated, we will wait forever until we have a better solution.
        while True:
            resp = k8s_core_api.list_namespaced_config_map(
                namespace=job_namespace,
                label_selector=labels,
            )

            logger.debug("Got %d config maps, expected %d", len(resp.items),
                         expected_num)
            if len(resp.items) == expected_num:
                items = resp.items
                break
            time.sleep(1)

        if len(items) != expected_num:
            logger.error(
                "timeout in waiting other's configmap, maybe because resource not enough"
            )
            sys.exit(ERROR_EXIT_CODE["wait_sync_fail"])

        for configmap in items:
            c_name = configmap.metadata.name
            role_idx = c_name.split("-")[-1]
            if role_idx.isnumeric():
                # created by launcher, have name "xxx-yyy-zzz-role-idx"
                role_idx = c_name.split("-")[-2] + role_idx

            sd_info = json.loads(configmap.data["pod.json"])
            ip = sd_info["ip"]
            ssh_port = sd_info["ssh_port"]
            envs["DLTS_SD_%s_IP" % role_idx] = ip
            envs["DLTS_SD_%s_SSH_PORT" % role_idx] = ssh_port

    path = Path(os.path.dirname(args.environment))
    path.mkdir(parents=True, exist_ok=True)

    export_env(args.environment, envs)


def get_logging_level():
    mapping = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING
    }

    result = logging.DEBUG

    if os.environ.get("LOGGING_LEVEL") is not None:
        level = os.environ["LOGGING_LEVEL"]
        result = mapping.get(level.upper())
        if result is None:
            sys.stderr.write("unknown logging level " + level +
                             ", default to INFO\n")
            result = logging.INFO

    return result


if __name__ == "__main__":
    logging.basicConfig(
        format=
        "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)s - %(message)s",
        level=get_logging_level())

    parser = argparse.ArgumentParser()

    parser.add_argument("--environment",
                        "-e",
                        help="path to generate environment",
                        default="/dlts-runtime/env/init.env")

    args = parser.parse_args()

    main(args)
