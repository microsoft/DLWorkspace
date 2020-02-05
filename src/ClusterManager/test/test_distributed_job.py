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
