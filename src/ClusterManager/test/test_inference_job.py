#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import time

import utils

logger = logging.getLogger(__file__)


@utils.case()
def test_inference_job_running(args):
    envs = {
        "DLWS_HOST_NETWORK": "",
        "DLTS_HOST_NETWORK": "",
        "DLWS_NUM_GPU_PER_WORKER": "1",
        "DLTS_NUM_GPU_PER_WORKER": "1",
        "DLWS_VC_NAME": str(args.vc),
        "DLTS_VC_NAME": str(args.vc),
        "DLWS_UID": str(args.uid),
        "DLTS_UID": str(args.uid),
        "DLWS_USER_NAME": args.email.split("@")[0],
        "DLTS_USER_NAME": args.email.split("@")[0],
        "DLWS_USER_EMAIL": args.email,
        "DLTS_USER_EMAIL": args.email,
        "DLWS_ROLE_NAME": "master",
        "DLTS_ROLE_NAME": "master",
        "DLWS_JOB_ID": "unknown",
        "DLTS_JOB_ID": "unknown",
    }

    job_spec = utils.gen_default_job_description("inference", args.email,
                                                 args.uid, args.vc)

    with utils.run_job(args.rest, job_spec) as job:
        state = job.block_until_state_not_in(
            {"unapproved", "queued", "scheduling"})
        assert state == "running"

        envs["DLWS_JOB_ID"] = job.jid
        envs["DLTS_JOB_ID"] = job.jid

        pods = utils.kube_get_pods(args.config, "default", "jobId=" + job.jid)
        assert len(pods) == 2

        for pod in pods:
            envs["DLWS_ROLE_NAME"] = pod.metadata.labels["jobRole"]
            envs["DLTS_ROLE_NAME"] = pod.metadata.labels["jobRole"]
            pod_name = pod.metadata.name
            container_name = pod.spec.containers[0].name

            cmd = ["bash", "-c"]

            remain_cmd = [
                "printf %s= ; printenv %s" % (key, key)
                for key, _ in envs.items()
            ]

            cmd.append(";".join(remain_cmd))

            code, output = utils.kube_pod_exec(args.config, "default", pod_name,
                                               container_name, cmd)

            logger.debug("cmd %s output for %s.%s is %s", cmd, pod_name,
                         container_name, output)

            for key, val in envs.items():
                expected_output = "%s=%s" % (key, val)
                assert output.find(
                    expected_output) != -1, "could not find %s in log %s" % (
                        expected_output, output)


@utils.case()
def test_inference_job_scale(args):
    if utils.get_launcher(args.config) == "controller":
        return
    job_spec = utils.gen_default_job_description("inference",
                                                 args.email,
                                                 args.uid,
                                                 args.vc,
                                                 cmd="sleep 600")

    with utils.run_job(args.rest, job_spec) as job:
        job_id = job.jid
        state = job.block_until_state_not_in(
            {"unapproved", "queued", "scheduling"})
        assert state == "running"

        deployment_name = job_id + "-deployment"
        deployment = utils.kube_get_deployment(args.config, "default",
                                               deployment_name)
        assert 1 == deployment.spec.replicas

        desired_replicas = 2
        logger.info("scale up job %s to %d" % (job_id, desired_replicas))
        resp = utils.scale_job(args.rest, args.email, job_id, desired_replicas)
        assert "Success" == resp

        time.sleep(30)
        deployment = utils.kube_get_deployment(args.config, "default",
                                               deployment_name)
        assert desired_replicas == deployment.spec.replicas

        desired_replicas = 1
        logger.info("scale down job %s to %d" % (job_id, desired_replicas))
        resp = utils.scale_job(args.rest, args.email, job_id, desired_replicas)
        assert "Success" == resp

        time.sleep(30)
        deployment = utils.kube_get_deployment(args.config, "default",
                                               deployment_name)
        assert desired_replicas == deployment.spec.replicas


@utils.case()
def test_inference_job_use_alias_to_run(args):
    job_spec = utils.gen_default_job_description(
        "inference",
        args.email,
        args.uid,
        args.vc,
        cmd="echo dummy `whoami` ; sleep 120")

    def satisified(expected, times, log):
        """ return True on found `expected` occurs `times` times in `log` """
        start = 0
        for _ in range(times):
            end = log.find(expected, start)
            if end == -1:
                return False
            start = end + 1
        return True

    expected_word = "dummy %s" % (args.email.split("@")[0])

    with utils.run_job(args.rest, job_spec) as job:
        state = job.block_until_state_not_in(
            {"unapproved", "queued", "scheduling"})
        assert state == "running"

        for _ in range(300):
            log = utils.get_job_log(args.rest, args.email, job.jid)
            if satisified(expected_word, 2, log):
                break
            time.sleep(0.5)

        assert satisified(expected_word, 2, log), 'log is %s' % (log)
