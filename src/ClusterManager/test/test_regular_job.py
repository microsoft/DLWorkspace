#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import time

import utils

logger = logging.getLogger(__file__)


@utils.case
def test_regular_job_running(args):
    expected = "wantThisInLog"
    cmd = "echo %s ; sleep 1800" % expected

    job_spec = utils.gen_default_job_description("regular",
                                                 args.email,
                                                 args.uid,
                                                 args.vc,
                                                 cmd=cmd)

    with utils.run_job(args.rest, job_spec) as job:
        state = job.block_until_state_not_in(
            {"unapproved", "queued", "scheduling"})
        assert state == "running"

        for _ in range(50):
            log = utils.get_job_log(args.rest, args.email, job.jid)

            if expected in log:
                break

            time.sleep(0.5)
        assert expected in log, 'assert {} in {}'.format(expected, log)


@utils.case
def test_data_job_running(args):
    expected_state = "finished"
    expected_word = "wantThisInLog"
    cmd = "mkdir -p /tmp/dlts_test_dir; " \
          "echo %s > /tmp/dlts_test_dir/testfile; " \
          "cd /DataUtils; " \
          "./copy_data.sh /tmp/dlts_test_dir adl://indexserveplatform-experiment-c09.azuredatalakestore.net/local/dlts_test_dir True 4194304 4 2; " \
          "./copy_data.sh adl://indexserveplatform-experiment-c09.azuredatalakestore.net/local/dlts_test_dir /tmp/dlts_test_dir_copyback False 33554432 4 2; " \
          "cat /tmp/dlts_test_dir_copyback/testfile; " % expected_word

    image = "indexserveregistry.azurecr.io/dlts-data-transfer-image:latest"

    job_spec = utils.gen_default_job_description("data",
                                                 args.email,
                                                 args.uid,
                                                 args.vc,
                                                 cmd=cmd,
                                                 image=image)
    with utils.run_job(args.rest, job_spec) as job:
        state = job.block_until_state_not_in(
            {"unapproved", "queued", "scheduling", "running"})
        assert expected_state == state

        for _ in range(10):
            log = utils.get_job_log(args.rest, args.email, job.jid)
            if expected_word in log:
                break
            time.sleep(0.5)

        assert expected_word in log, 'assert {} in {}'.format(
            expected_word, log)


@utils.case
def test_job_fail(args):
    expected_state = "failed"
    cmd = "false"

    job_spec = utils.gen_default_job_description("regular",
                                                 args.email,
                                                 args.uid,
                                                 args.vc,
                                                 cmd=cmd)
    with utils.run_job(args.rest, job_spec) as job:
        state = job.block_until_state_not_in(
            {"unapproved", "queued", "scheduling", "running"})
        assert expected_state == state


@utils.case
def test_op_job(args):
    job_spec = utils.gen_default_job_description("regular", args.email,
                                                 args.uid, args.vc)

    with utils.run_job(args.rest, job_spec) as job:
        job_id = job.jid
        utils.block_until_state_in(args.rest, job_id, {"running"})

        # Try to ApproveJob
        logger.info("approve job %s" % job_id)
        resp = utils.approve_job(args.rest, args.email, job_id)
        assert "Cannot approve the job. Job ID:%s" % job_id == resp["result"]

        # PauseJob
        logger.info("pause job %s" % job_id)
        resp = utils.pause_job(args.rest, args.email, job_id)
        assert "Success, the job is scheduled to be paused." == resp["result"]

        # ResumeJob
        utils.block_until_state_in(args.rest, job_id, {"paused"})
        logger.info("resume job %s" % job_id)
        resp = utils.resume_job(args.rest, args.email, job_id)
        assert "Success, the job is scheduled to be resumed." == resp["result"]

        # KillJob
        utils.block_until_state_in(args.rest, job_id, {"running"})
        logger.info("kill job %s" % job_id)
        resp = utils.kill_job(args.rest, args.email, job_id)
        assert "Success, the job is scheduled to be terminated." == resp[
            "result"]

        state = job.block_until_state_not_in({"killing"})
        assert "killed" == state


@utils.case
def test_batch_op_jobs(args):
    num_jobs = 2
    job_ids = []

    job_spec = utils.gen_default_job_description("regular", args.email,
                                                 args.uid, args.vc)
    for i in range(num_jobs):
        job_id = utils.post_job(args.rest, job_spec)
        job_ids.append(job_id)

    # FIXME there is a race condition between rest and jobmanager
    # E.g. kill job request comes in when jobmanager is processing an unapproved
    # job. "killing" will be overriden by "queued".
    for job_id in job_ids:
        utils.block_until_state_in(args.rest, job_id, {"running"})

    # Try to ApproveJobs
    logger.info("approve jobs %s" % job_ids)
    resp = utils.approve_jobs(args.rest, args.email, job_ids)
    for _, msg in resp["result"].items():
        assert "cannot approve a(n) \"running\" job" == msg

    # PauseJobs
    logger.info("pause jobs %s" % job_ids)
    resp = utils.pause_jobs(args.rest, args.email, job_ids)
    for _, msg in resp["result"].items():
        assert "successfully paused" == msg

    # ResumeJob
    for job_id in job_ids:
        utils.block_until_state_in(args.rest, job_id, {"paused"})
    logger.info("resume jobs %s" % job_ids)
    resp = utils.resume_jobs(args.rest, args.email, job_ids)
    for _, msg in resp["result"].items():
        assert "successfully resumed" == msg

    # KillJob
    for job_id in job_ids:
        utils.block_until_state_in(args.rest, job_id, {"running"})
    logger.info("kill jobs %s" % job_ids)
    resp = utils.kill_jobs(args.rest, args.email, job_ids)
    for _, msg in resp["result"].items():
        assert "successfully killed" == msg

    for job_id in job_ids:
        state = utils.block_until_state_not_in(args.rest, job_id, {"killing"})
        assert "killed" == state


@utils.case
def test_batch_kill_jobs(args):
    expected_msg = "successfully killed"
    expected_state = "killed"

    job_spec = utils.gen_default_job_description("regular", args.email,
                                                 args.uid, args.vc)

    num_jobs = 2
    job_ids = []
    for i in range(num_jobs):
        job_id = utils.post_job(args.rest, job_spec)
        job_ids.append(job_id)

    # FIXME there is a race condition between rest and jobmanager
    # E.g. kill job request comes in when jobmanager is processing an unapproved
    # job. "killing" will be overriden by "queued".
    for job_id in job_ids:
        state = utils.block_until_state_not_in(
            args.rest, job_id, {"unapproved", "queued", "scheduling"})
        assert state == "running"

    resp = utils.kill_jobs(args.rest, args.email,
                           [job_id for job_id in job_ids])

    assert isinstance(resp["result"], dict)
    assert len(resp["result"]) == num_jobs
    for _, msg in resp["result"].items():
        assert expected_msg == msg

    for job_id in job_ids:
        state = utils.block_until_state_not_in(args.rest, job_id, {"killing"})
        assert expected_state == state


@utils.case
def test_regular_job_ssh(args):
    job_spec = utils.gen_default_job_description("regular", args.email,
                                                 args.uid, args.vc)

    with utils.run_job(args.rest, job_spec) as job:
        endpoints = utils.create_endpoint(args.rest, args.email, job.jid,
                                          ["ssh"])
        endpoints_ids = list(endpoints.keys())
        assert len(endpoints_ids) == 1
        endpoint_id = endpoints_ids[0]

        state = job.block_until_state_not_in(
            {"unapproved", "queued", "scheduling"})
        assert state == "running"

        ssh_endpoint = utils.wait_endpoint_ready(args.rest, args.email,
                                                 job.jid, endpoint_id)
        logger.debug("endpoints resp is %s", ssh_endpoint)

        ssh_host = "%s.%s" % (ssh_endpoint["nodeName"], ssh_endpoint["domain"])
        ssh_port = ssh_endpoint["port"]

        # exec into jobmanager to execute ssh to avoid firewall
        job_manager_pod = utils.kube_get_pods(args.config, "default",
                                              "app=jobmanager")[0]
        job_manager_pod_name = job_manager_pod.metadata.name

        alias = args.email.split("@")[0]

        cmd = [
            "ssh", "-i",
            "/dlwsdata/work/%s/.ssh/id_rsa" % alias, "-p", ssh_port, "-o",
            "StrictHostKeyChecking=no", "-o", "LogLevel=ERROR",
            "%s@%s" % (alias, ssh_host), "--", "echo", "dummy"
        ]
        code, output = utils.kube_pod_exec(args.config, "default",
                                           job_manager_pod_name, "jobmanager",
                                           cmd)
        assert code == 0, "code is %s, output is %s" % (code, output)
        assert output == "dummy\n", "output is %s" % (output)


@utils.case
def test_list_all_jobs(args):
    job_spec = utils.gen_default_job_description("regular",
                                                 args.email,
                                                 args.uid,
                                                 args.vc,
                                                 cmd="")

    # All jobs should include finished jobs
    with utils.run_job(args.rest, job_spec) as job:
        job_id = job.jid
        state = job.block_until_state_not_in(
            {"unapproved", "queued", "scheduling", "running"})
        assert state == "finished"

    resp = utils.get_job_list(args.rest, args.email, args.vc, "all", 10)
    finished_jobs = resp.get("finishedJobs", None)
    assert isinstance(finished_jobs, list)

    finished_job_ids = [job["jobId"] for job in finished_jobs]
    assert job_id in finished_job_ids


@utils.case
def test_regular_job_env(args):
    envs = {
        "DLWS_HOST_NETWORK": "",
        "DLWS_NUM_PS": "0",
        "DLWS_NUM_WORKER": "1",
        "DLWS_NUM_GPU_PER_WORKER": "0",
        "DLWS_VC_NAME": str(args.vc),
        "DLWS_UID": str(args.uid),
        "DLWS_USER_NAME": args.email.split("@")[0],
        "DLWS_USER_EMAIL": args.email,
        "DLWS_ROLE_NAME": "master",
        "DLWS_JOB_ID": "unknown",
    }

    cmd = []
    for key, _ in envs.items():
        cmd.append("printf %s=" % key)
        cmd.append("printenv %s" % key)

    cmd.append("echo 'well' 'done'")
    cmd = "\n".join(cmd)

    job_spec = utils.gen_default_job_description("regular",
                                                 args.email,
                                                 args.uid,
                                                 args.vc,
                                                 cmd=cmd)

    with utils.run_job(args.rest, job_spec) as job:
        state = job.block_until_state_not_in(
            {"unapproved", "queued", "scheduling", "running"})
        assert state == "finished"
        envs["DLWS_JOB_ID"] = job.jid

        for _ in range(10):
            log = utils.get_job_log(args.rest, args.email, job.jid)
            if 'well done' in log:
                break
            time.sleep(0.5)

        for key, val in envs.items():
            expected_output = "%s=%s" % (key, val)
            assert log.find(
                expected_output) != -1, "could not find %s in log %s" % (
                    expected_output, log)


@utils.case
def test_blobfuse(args):
    path = "/tmp/blob/${DLWS_JOB_ID}"
    cmd = "echo dummy > %s; cat %s ; rm %s" % (path, path, path)

    job_spec = utils.gen_default_job_description("regular",
                                                 args.email,
                                                 args.uid,
                                                 args.vc,
                                                 cmd=cmd)

    job_spec["plugins"] = utils.load_azure_blob_config(args.config,
                                                       "/tmp/blob")

    with utils.run_job(args.rest, job_spec) as job:
        state = job.block_until_state_not_in(
            {"unapproved", "queued", "scheduling", "running"})
        assert state == "finished"

        for _ in range(10):
            log = utils.get_job_log(args.rest, args.email, job.jid)
            if log.find("dummy") != -1:
                break
            time.sleep(0.5)

        assert log.find("dummy") != -1, "could not find %s in log %s" % (
            "dummy", log)


@utils.case
def test_sudo_installed(args):
    cmd = "sudo ls"
    image = "pytorch/pytorch:latest"  # no sudo installed in this image

    job_spec = utils.gen_default_job_description(
        "regular",
        args.email,
        args.uid,
        args.vc,
        cmd=cmd,
        image=image,
    )

    with utils.run_job(args.rest, job_spec) as job:
        state = job.block_until_state_not_in(
            {"unapproved", "queued", "scheduling", "running"})
        log = utils.get_job_log(args.rest, args.email, job.jid)

        assert state == "finished"
