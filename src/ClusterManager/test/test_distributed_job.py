#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import time
import copy

import utils

logger = logging.getLogger(__file__)


@utils.case
def test_distributed_job_running(args):
    expected = "wantThisInLog"
    cmd = "echo %s ; sleep 1800" % expected

    with utils.run_job(args.rest,
                       "distributed",
                       args.email,
                       args.uid,
                       args.vc,
                       cmd=cmd) as job:
        state = utils.block_until_state_not_in(
            args.rest, job.jid, {"unapproved", "queued", "scheduling"})
        assert state == "running"

        for _ in range(10):
            log = utils.get_job_log(args.rest, args.email, job.jid)

            if expected not in log["log"]:
                time.sleep(0.5)
        assert expected in log["log"]


@utils.case
def test_distributed_job_ssh(args):
    with utils.run_job(args.rest, "distributed", args.email, args.uid,
                       args.vc) as job:
        endpoints = utils.create_endpoint(args.rest, args.email, job.jid,
                                          ["ssh"])
        endpoints_ids = list(endpoints.keys())
        assert len(endpoints_ids) == 2

        state = utils.block_until_state_not_in(
            args.rest, job.jid, {"unapproved", "queued", "scheduling"})
        assert state == "running"

        for endpoint_id in endpoints_ids:
            ssh_endpoint = utils.wait_endpoint_ready(args.rest, args.email,
                                                     job.jid, endpoint_id)
            logger.debug("endpoint_id is %s, endpoints resp is %s",
                         endpoint_id, ssh_endpoint)

            ssh_host = "%s.%s" % (ssh_endpoint["nodeName"],
                                  ssh_endpoint["domain"])
            ssh_port = ssh_endpoint["port"]

            # exec into jobmanager to execute ssh to avoid firewall
            job_manager_pod = utils.kube_get_pods(args.config, "default",
                                                  "app=jobmanager")[0]
            job_manager_pod_name = job_manager_pod.metadata.name

            alias = args.email.split("@")[0]

            cmd_prefix = [
                "ssh",
                "-i",
                "/dlwsdata/work/%s/.ssh/id_rsa" % alias,
                "-p",
                ssh_port,
                "-o",
                "StrictHostKeyChecking=no",
                "-o",
                "LogLevel=ERROR",
                "%s@%s" % (alias, ssh_host),
                "--",
            ]

            # check they can connect to each other
            for role in ["ps-0", "worker-0"]:
                cmd = copy.deepcopy(cmd_prefix)
                cmd.extend([
                    "ssh", role, "-o", "LogLevel=ERROR", "--", "echo", "dummy"
                ])
                code, output = utils.kube_pod_exec(args.config, "default",
                                                   job_manager_pod_name,
                                                   "jobmanager", cmd)
                logger.debug("code %s, output '%s'", code, output)
                assert code == 0
                assert output == "dummy\n"


@utils.case
def test_distributed_job_env(args):
    envs = {
        "DLWS_HOST_NETWORK": "enable",
        "DLWS_NUM_PS": "1",
        "DLWS_NUM_WORKER": "1",
        "DLWS_NUM_GPU_PER_WORKER": "0",
        "DLWS_VC_NAME": str(args.vc),
        "DLWS_UID": str(args.uid),
        "DLWS_USER_NAME": args.email.split("@")[0],
        "DLWS_USER_EMAIL": args.email,
        "DLWS_ROLE_NAME": "master",
        "DLWS_JOB_ID": "unknown",
        "DLWS_ROLE_IDX": "0",
    }

    with utils.run_job(args.rest, "distributed", args.email, args.uid,
                       args.vc) as job:
        state = utils.block_until_state_not_in(
            args.rest, job.jid, {"unapproved", "queued", "scheduling"})
        assert state == "running"
        envs["DLWS_JOB_ID"] = job.jid

        pods = utils.kube_get_pods(args.config, "default", "jobId=" + job.jid)
        assert len(pods) == 2

        for pod in pods:
            envs["DLWS_ROLE_NAME"] = pod.metadata.labels["jobRole"]
            pod_name = pod.metadata.name
            container_name = pod.spec.containers[0].name

            cmd = ["bash", "-c"]

            remain_cmd = [
                "printf %s= ; printenv %s" % (key, key)
                for key, _ in envs.items()
            ]

            cmd.append(";".join(remain_cmd))

            code, output = utils.kube_pod_exec(args.config, "default",
                                               pod_name, container_name, cmd)

            logger.debug("cmd %s output for %s.%s is %s", cmd, pod_name,
                         container_name, output)

            for key, val in envs.items():
                expected_output = "%s=%s" % (key, val)
                assert output.find(
                    expected_output) != -1, "could not find %s in log %s" % (
                        expected_output, output)
