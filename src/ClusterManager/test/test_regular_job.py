#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import time

import utils

logger = logging.getLogger(__file__)


def test_regular_job_running(args, preemptable=False):
    expected = "wantThisInLog"
    cmd = "echo %s ; sleep 120" % expected

    job_spec = utils.gen_default_job_description("regular",
                                                 args.email,
                                                 args.uid,
                                                 args.vc,
                                                 preemptable=preemptable,
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


@utils.case(unstable=True)
def test_regular_non_preemptable_job_running(args):
    test_regular_job_running(args)


@utils.case(unstable=True)
def test_regular_preemptable_job_running(args):
    test_regular_job_running(args, True)


@utils.case(unstable=True)
def test_data_job_running(args):
    expected_word = "wantThisInLog"
    cmd = "mkdir -p /tmp/dlts_test_dir; " \
          "echo %s > /tmp/dlts_test_dir/testfile; " \
          "cd /DataUtils; " \
          "./copy_data.sh /tmp/dlts_test_dir adl://indexserveplatform-experiment-c09.azuredatalakestore.net/local/dlts_test_dir True 4194304 4 2 >/dev/null 2>&1;" \
          "./copy_data.sh adl://indexserveplatform-experiment-c09.azuredatalakestore.net/local/dlts_test_dir /tmp/dlts_test_dir_copyback False 33554432 4 2 >/dev/null 2>&1;" \
          "cat /tmp/dlts_test_dir_copyback/testfile; sleep 120" % expected_word

    image = "indexserveregistry.azurecr.io/dlts-data-transfer-image:latest"

    job_spec = utils.gen_default_job_description("data",
                                                 args.email,
                                                 args.uid,
                                                 args.vc,
                                                 cmd=cmd,
                                                 image=image)
    with utils.run_job(args.rest, job_spec) as job:
        state = job.block_until_state_not_in(
            {"unapproved", "queued", "scheduling"})

        for _ in range(300):
            log = utils.get_job_log(args.rest, args.email, job.jid)
            if expected_word in log:
                break
            time.sleep(0.5)
        assert expected_word in log, 'assert {} in {}'.format(
            expected_word, log)


@utils.case()
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


@utils.case()
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
        resp = utils.kill_job(args.rest, args.email, job_id, "testing kill job")
        assert "Success, the job is scheduled to be terminated." == resp[
            "result"]

        state = job.block_until_state_not_in({"killing"})
        assert "killed" == state


@utils.case()
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


@utils.case()
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


@utils.case()
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

        ssh_endpoint = utils.wait_endpoint_state(args.rest, args.email, job.jid,
                                                 endpoint_id)
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


@utils.case(unstable=True)
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


@utils.case()
def test_regular_job_env(args):
    envs = {
        "DLWS_HOST_NETWORK": "",
        "DLTS_HOST_NETWORK": "",
        "DLWS_NUM_PS": "0",
        "DLTS_NUM_PS": "0",
        "DLWS_NUM_WORKER": "1",
        "DLTS_NUM_WORKER": "1",
        "DLWS_NUM_GPU_PER_WORKER": "0",
        "DLTS_NUM_GPU_PER_WORKER": "0",
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

    job_spec = utils.gen_default_job_description("regular", args.email,
                                                 args.uid, args.vc)

    with utils.run_job(args.rest, job_spec) as job:
        envs["DLWS_JOB_ID"] = job.jid
        envs["DLTS_JOB_ID"] = job.jid

        endpoints = utils.create_endpoint(args.rest, args.email, job.jid,
                                          ["ssh"])
        endpoints_ids = list(endpoints.keys())
        assert len(endpoints_ids) == 1
        endpoint_id = endpoints_ids[0]

        state = job.block_until_state_not_in(
            {"unapproved", "queued", "scheduling"})
        assert state == "running"

        ssh_endpoint = utils.wait_endpoint_state(args.rest, args.email, job.jid,
                                                 endpoint_id)
        logger.debug("endpoints resp is %s", ssh_endpoint)

        ssh_host = "%s.%s" % (ssh_endpoint["nodeName"], ssh_endpoint["domain"])
        ssh_port = ssh_endpoint["port"]

        # exec into jobmanager to execute ssh to avoid firewall
        job_manager_pod = utils.kube_get_pods(args.config, "default",
                                              "app=jobmanager")[0]
        job_manager_pod_name = job_manager_pod.metadata.name

        alias = args.email.split("@")[0]

        bash_cmd = ";".join([
            "printf '%s=' ; printenv %s" % (key, key)
            for key, _ in envs.items()
        ])

        ssh_cmd = [
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
        ssh_cmd.append(bash_cmd)
        code, output = utils.kube_pod_exec(args.config, "default",
                                           job_manager_pod_name, "jobmanager",
                                           ssh_cmd)
        assert code == 0, "code is %s, output is %s" % (code, output)

        for key, val in envs.items():
            expected_output = "%s=%s" % (key, val)
            assert output.find(
                expected_output) != -1, "could not find %s in log %s" % (
                    expected_output, output)


@utils.case(unstable=True)
def test_blobfuse(args):
    path = "/tmp/blob/${DLTS_JOB_ID}"
    cmd = "echo dummy > %s; cat %s ; rm %s ;" % (path, path, path)

    job_spec = utils.gen_default_job_description("regular",
                                                 args.email,
                                                 args.uid,
                                                 args.vc,
                                                 cmd=cmd)

    job_spec["plugins"] = utils.load_azure_blob_config(args.config, "/tmp/blob")

    with utils.run_job(args.rest, job_spec) as job:
        state = job.block_until_state_not_in(
            {"unapproved", "queued", "scheduling", "running"})
        assert state == "finished", "state is not finished, but %s" % state

        for _ in range(5):
            log = utils.get_job_log(args.rest, args.email, job.jid)
            if log.find("dummy") != -1:
                break
            time.sleep(0.5)

        assert log.find("dummy") != -1, "could not find dummy in log %s" % (log)


@utils.case(unstable=True)
def test_sudo_installed(args):
    cmd = "sudo ls"
    image = "pytorch/pytorch:latest" # no sudo installed in this image

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


@utils.case()
def test_regular_job_custom_ssh_key(args):
    job_spec = utils.gen_default_job_description("regular", args.email,
                                                 args.uid, args.vc)
    with open("data/id_rsa.pub") as f:
        job_spec["ssh_public_keys"] = [f.read()]

    with utils.run_job(args.rest, job_spec) as job:
        endpoints = utils.create_endpoint(args.rest, args.email, job.jid,
                                          ["ssh"])
        endpoints_ids = list(endpoints.keys())
        assert len(endpoints_ids) == 1
        endpoint_id = endpoints_ids[0]

        state = job.block_until_state_not_in(
            {"unapproved", "queued", "scheduling"})
        assert state == "running"

        ssh_endpoint = utils.wait_endpoint_state(args.rest, args.email, job.jid,
                                                 endpoint_id)
        logger.debug("endpoints resp is %s", ssh_endpoint)

        ssh_host = "%s.%s" % (ssh_endpoint["nodeName"], ssh_endpoint["domain"])
        ssh_port = ssh_endpoint["port"]

        # exec into jobmanager to execute ssh to avoid firewall
        job_manager_pod = utils.kube_get_pods(args.config, "default",
                                              "app=jobmanager")[0]
        job_manager_pod_name = job_manager_pod.metadata.name

        alias = args.email.split("@")[0]

        dest = "/tmp/test_regular_job_customer_ssh_key"

        script_cmd = []

        with open("data/id_rsa") as f:
            script_cmd.append("rm %s ; " % dest)

            for line in f.readlines():
                script_cmd.append("echo")
                script_cmd.append(line.strip())
                script_cmd.append(">> %s ;" % dest)

            script_cmd.append("chmod 400 %s ;" % dest)

        cmd = ["sh", "-c", " ".join(script_cmd)]

        code, output = utils.kube_pod_exec(args.config, "default",
                                           job_manager_pod_name, "jobmanager",
                                           cmd)
        assert code == 0, "code is %s, output is %s" % (code, output)

        cmd = [
            "ssh", "-i", dest, "-p", ssh_port, "-o", "StrictHostKeyChecking=no",
            "-o", "LogLevel=ERROR",
            "%s@%s" % (alias, ssh_host), "--", "echo", "dummy"
        ]
        code, output = utils.kube_pod_exec(args.config, "default",
                                           job_manager_pod_name, "jobmanager",
                                           cmd)
        assert code == 0, "code is %s, output is %s" % (code, output)
        assert output == "dummy\n", "output is %s" % (output)


@utils.case(unstable=True)
def test_do_not_expose_private_key(args):
    cmd = "echo a ; printenv DLTS_SSH_PRIVATE_KEY ; echo b"

    job_spec = utils.gen_default_job_description("regular",
                                                 args.email,
                                                 args.uid,
                                                 args.vc,
                                                 cmd=cmd)

    with utils.run_job(args.rest, job_spec) as job:
        state = job.block_until_state_not_in(
            {"unapproved", "queued", "scheduling", "running"})
        assert state == "finished"

        expected = "a\nb"

        for _ in range(50):
            log = utils.get_job_log(args.rest, args.email, job.jid)

            if expected in log:
                break

            time.sleep(0.5)
        assert expected in log, 'assert {} in {}'.format(expected, log)


@utils.case()
def test_ssh_do_not_expose_private_key(args):
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

        ssh_endpoint = utils.wait_endpoint_state(args.rest, args.email, job.jid,
                                                 endpoint_id)

        ssh_host = "%s.%s" % (ssh_endpoint["nodeName"], ssh_endpoint["domain"])
        ssh_port = ssh_endpoint["port"]

        # exec into jobmanager to execute ssh to avoid firewall
        job_manager_pod = utils.kube_get_pods(args.config, "default",
                                              "app=jobmanager")[0]
        job_manager_pod_name = job_manager_pod.metadata.name

        alias = args.email.split("@")[0]

        ssh_cmd = [
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
            "echo a ; printenv DLTS_SSH_PRIVATE_KEY ; echo b",
        ]
        code, output = utils.kube_pod_exec(args.config, "default",
                                           job_manager_pod_name, "jobmanager",
                                           ssh_cmd)
        assert code == 0, "code is %s, output is %s" % (code, output)

        expected = "a\nb"
        assert expected in output, "could not find %s in output %s" % (expected,
                                                                       output)


def test_ssh_cuda_visible_devices(args, job_spec, expected):
    with utils.run_job(args.rest, job_spec) as job:
        endpoints = utils.create_endpoint(args.rest, args.email, job.jid,
                                          ["ssh"])
        endpoints_ids = list(endpoints.keys())
        assert len(endpoints_ids) == 1
        endpoint_id = endpoints_ids[0]

        state = job.block_until_state_not_in(
            {"unapproved", "queued", "scheduling"})
        assert state == "running"

        ssh_endpoint = utils.wait_endpoint_state(args.rest, args.email, job.jid,
                                                 endpoint_id)

        ssh_host = "%s.%s" % (ssh_endpoint["nodeName"], ssh_endpoint["domain"])
        ssh_port = ssh_endpoint["port"]

        # exec into jobmanager to execute ssh to avoid firewall
        job_manager_pod = utils.kube_get_pods(args.config, "default",
                                              "app=jobmanager")[0]
        job_manager_pod_name = job_manager_pod.metadata.name

        alias = args.email.split("@")[0]

        ssh_cmd = [
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
            "echo a; env | grep CUDA_VISIBLE_DEVICES;",
            "grep CUDA_VISIBLE_DEVICES ~/.ssh/environment; echo b",
        ]
        code, output = utils.kube_pod_exec(args.config, "default",
                                           job_manager_pod_name, "jobmanager",
                                           ssh_cmd)
        assert code == 0, "code is %s, output is %s" % (code, output)

        assert expected in output, "could not find %s in output %s" % (expected,
                                                                       output)


@utils.case()
def test_ssh_cpu_job_cuda_visible_devices(args):
    job_spec = utils.gen_default_job_description("regular", args.email,
                                                 args.uid, args.vc)
    expected = "a\nb"
    test_ssh_cuda_visible_devices(args, job_spec, expected)


@utils.case()
def test_ssh_one_gpu_job_cuda_visible_devices(args):
    job_spec = utils.gen_default_job_description("regular",
                                                 args.email,
                                                 args.uid,
                                                 args.vc,
                                                 resourcegpu=1)

    expected = "a\nb"
    test_ssh_cuda_visible_devices(args, job_spec, expected)


@utils.case()
def test_ssh_multi_gpu_job_cuda_visible_devices(args):
    job_spec = utils.gen_default_job_description("regular",
                                                 args.email,
                                                 args.uid,
                                                 args.vc,
                                                 resourcegpu=2)

    expected = "a\nCUDA_VISIBLE_DEVICES=0,1\nCUDA_VISIBLE_DEVICES=0,1\nb"
    test_ssh_cuda_visible_devices(args, job_spec, expected)


@utils.case()
def test_fault_tolerance(args):
    # Job is only retried when launcher is controller.
    if utils.get_launcher(args.config) == "python":
        return

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

        ssh_endpoint = utils.wait_endpoint_state(args.rest, args.email, job.jid,
                                                 endpoint_id)
        ssh_host = "%s.%s" % (ssh_endpoint["nodeName"], ssh_endpoint["domain"])
        ssh_port = ssh_endpoint["port"]

        logger.info("current ssh endpoint is %s:%s", ssh_host, ssh_port)

        pod = utils.kube_get_pods(args.config, "default",
                                  "jobId=%s" % (job.jid))[0]
        utils.kube_delete_pod(args.config, "default", pod.metadata.name)

        ssh_endpoint = utils.wait_endpoint_state(args.rest,
                                                 args.email,
                                                 job.jid,
                                                 endpoint_id,
                                                 state="pending")

        ssh_endpoint = utils.wait_endpoint_state(args.rest, args.email, job.jid,
                                                 endpoint_id)

        ssh_host = "%s.%s" % (ssh_endpoint["nodeName"], ssh_endpoint["domain"])
        ssh_port = ssh_endpoint["port"]
        logger.info("current ssh endpoint is %s:%s", ssh_host, ssh_port)

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


@utils.case()
def test_no_resource_info(args):
    expected = "Insufficient nvidia.com/gpu"

    job_spec = utils.gen_default_job_description("regular",
                                                 args.email,
                                                 args.uid,
                                                 args.vc,
                                                 resourcegpu=5)
    # TODO hardcode 5 here, may need to change to `gpu_per_host + 1` manually
    # when testing other clusters

    with utils.run_job(args.rest, job_spec) as job:
        state = job.block_until_state_not_in({"unapproved", "queued"})
        assert state == "scheduling"

        for _ in range(50):
            details = utils.get_job_detail(args.rest, args.email, job.jid)

            message = utils.walk_json_safe(details, "jobStatusDetail", 0,
                                           "message")
            if expected in message:
                break

            time.sleep(0.5)
        assert expected in message, "unexpected detail " + details


@utils.case()
def test_regular_job_mountpoints(args):
    job_spec = utils.gen_default_job_description("regular", args.email,
                                                 args.uid, args.vc)

    with utils.run_job(args.rest, job_spec) as job:
        state = job.block_until_state_not_in({"unapproved", "queued"})
        assert state in ["scheduling", "running"]

        pod = utils.kube_get_pods(args.config, "default",
                                  "jobId=%s" % job.jid)[0]

        mps = utils.load_cluster_nfs_mountpoints(args, job.jid)
        mps.extend(utils.load_system_mountpoints(args))

        for mp in mps:
            assert utils.mountpoint_in_pod(mp, pod), \
                "mountpoint %s not in regular job %s" % (mp, job.jid)

        # Regular job should not have IB mounted
        ib_mps = utils.load_infiniband_mounts(args)
        for mp in ib_mps:
            assert not utils.mountpoint_in_pod(mp, pod), \
                "infiniband mountpoint %s in regular job %s" % (mp, job.jid)


@utils.case()
def test_job_insight(args):
    job_spec = utils.gen_default_job_description("regular", args.email,
                                                 args.uid, args.vc)

    with utils.run_job(args.rest, job_spec) as job:
        state = job.block_until_state_not_in(
            {"unapproved", "queued", "scheduling"})
        assert state == "running"

        payload = {"messages": ["dummy"]}
        resp = utils.set_job_insight(args.rest, args.email, job.jid, payload)
        assert resp.status_code == 200

        insight = utils.get_job_insight(args.rest, args.email, job.jid)
        assert payload == insight


@utils.case()
def test_gpu_type_override(args):
    job_spec = utils.gen_default_job_description("regular", args.email,
                                                 args.uid, args.vc)
    # wrong gpu type
    job_spec["gpuType"] = "V100"

    with utils.run_job(args.rest, job_spec) as job:
        state = job.block_until_state_not_in({"unapproved", "queued"})
        assert state in ["scheduling", "running"]

        pod = utils.kube_get_pods(args.config, "default",
                                  "jobId=%s" % job.jid)[0]

        # gpu type should be overriden by the correct one
        assert pod.metadata.labels.get("gpuType") == "P40"


@utils.case()
def test_job_priority(args):
    job_spec = utils.gen_default_job_description("regular", args.email,
                                                 args.uid, args.vc)
    with utils.run_job(args.rest, job_spec) as job:
        # wait until running to avoid state change race
        state = job.block_until_state_not_in({"unapproved", "queued"})
        assert state in ["scheduling", "running"]

        # invalid payload
        resp = utils.set_job_priorities(args.rest, args.email, None)
        assert resp.status_code == 400

        # unauthorized user cannot change priority
        resp = utils.set_job_priorities(args.rest, "unauthorized_user",
                                        {job.jid: 101})
        assert resp.status_code == 403
        priority = utils.get_job_priorities(args.rest)[job.jid]
        assert priority == 100

        # job owner can change priority
        resp = utils.set_job_priorities(args.rest, args.email, {job.jid: 101})
        assert resp.status_code == 200
        priority = utils.get_job_priorities(args.rest)[job.jid]
        assert priority == 101


@utils.case()
def test_regular_job_no_distributed_system_envs(args):
    envs = utils.load_distributed_system_envs(args)

    job_spec = utils.gen_default_job_description("regular",
                                                 args.email,
                                                 args.uid,
                                                 args.vc,
                                                 cmd="sleep infinity")
    with utils.run_job(args.rest, job_spec) as job:
        endpoints = utils.create_endpoint(args.rest, args.email, job.jid,
                                          ["ssh"])
        endpoint_id = list(endpoints.keys())[0]

        state = job.block_until_state_not_in(
            {"unapproved", "queued", "scheduling"})
        assert state == "running"

        ssh_endpoint = utils.wait_endpoint_state(args.rest, args.email, job.jid,
                                                 endpoint_id)
        logger.debug("endpoints resp is %s", ssh_endpoint)

        ssh_host = "%s.%s" % (ssh_endpoint["nodeName"], ssh_endpoint["domain"])
        ssh_port = ssh_endpoint["port"]
        ssh_id = ssh_endpoint["id"]

        bash_cmd = ";".join([
            "printf '%s=' ; printenv %s" % (key, key)
            for key, _ in envs.items()
        ])

        # exec into jobmanager to execute ssh to avoid firewall
        job_manager_pod = utils.kube_get_pods(args.config, "default",
                                              "app=jobmanager")[0]
        job_manager_pod_name = job_manager_pod.metadata.name

        alias = args.email.split("@")[0]

        ssh_cmd = [
            "ssh",
            "-i",
            "/dlwsdata/work/%s/.ssh/id_rsa" % alias,
            "-p",
            str(ssh_port),
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "LogLevel=ERROR",
            "%s@%s" % (alias, ssh_host),
            "--",
        ]
        ssh_cmd.append(bash_cmd)

        code, output = utils.kube_pod_exec(args.config, "default",
                                           job_manager_pod_name, "jobmanager",
                                           ssh_cmd)

        logger.debug("cmd %s code is %s, output is %s", " ".join(ssh_cmd), code,
                     output)

        for key, val in envs.items():
            expected_output = "%s=%s" % (key, val)
            assert output.find(
                expected_output) == -1, "should not find %s in log %s" % (
                    expected_output, output)


@utils.case()
def test_do_not_starve_big_job(args):
    big_job_spec = utils.gen_default_job_description("regular",
                                                     args.email,
                                                     args.uid,
                                                     args.vc,
                                                     resourcegpu=100)
    big_job_spec["jobName"] += ".big_job"
    small_job_spec = utils.gen_default_job_description("regular", args.email,
                                                       args.uid, args.vc)
    small_job_spec["jobName"] += ".small_job"

    with utils.run_job(args.rest, big_job_spec) as big_job:
        with utils.run_job(args.rest, small_job_spec) as small_job:
            state = small_job.block_until_state_not_in({"unapproved"})
            assert state == "queued"

            state = utils.get_job_status(args.rest, big_job.jid)["jobStatus"]
            # if vc has user_quota, it will be unapproved
            assert state in {"queued", "unapproved"}

            expected = "blocked by job with higher priority"
            for _ in range(50):
                details = utils.get_job_detail(args.rest, args.email,
                                               small_job.jid)

                message = utils.walk_json_safe(details, "jobStatusDetail", 0,
                                               "message")
                if expected in message:
                    break

                time.sleep(0.5)
            assert expected in message, "unexpected detail " + details


@utils.case()
def test_do_not_starve_preemptible_job(args):
    big_job_spec = utils.gen_default_job_description("regular",
                                                     args.email,
                                                     args.uid,
                                                     args.vc,
                                                     resourcegpu=100)
    big_job_spec["jobName"] += ".big_job"
    p_job_spec = utils.gen_default_job_description("regular",
                                                   args.email,
                                                   args.uid,
                                                   args.vc,
                                                   preemptable=True)
    p_job_spec["jobName"] += ".p_job"

    with utils.run_job(args.rest, big_job_spec) as big_job:
        with utils.run_job(args.rest, p_job_spec) as p_job:
            state = p_job.block_until_state_not_in(
                {"unapproved", "queued", "scheduling"})
            assert state == "running"

            state = utils.get_job_status(args.rest, big_job.jid)["jobStatus"]
            # if vc has user_quota, it will be unapproved
            assert state in {"queued", "unapproved"}


@utils.case()
def test_set_max_time_works(args):
    job_spec = utils.gen_default_job_description("regular", args.email,
                                                 args.uid, args.vc)

    with utils.run_job(args.rest, job_spec) as job:
        state = job.block_until_state_not_in(
            {"unapproved", "queued", "scheduling"})
        assert state == "running"

        resp = utils.set_job_max_time(args.rest, args.email, job.jid, 1)
        assert resp.status_code == 200, "get %d, are you admin?" % (
            resp.status_code)

        state = job.block_until_state_not_in({"running"}, timeout=30)
        assert state == "killed"


@utils.case()
def test_endpoint_role(args):
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

        ssh_endpoint = utils.wait_endpoint_state(args.rest, args.email, job.jid,
                                                 endpoint_id)
        role_name = ssh_endpoint.get("role-name")
        role_idx = ssh_endpoint.get("role-idx")
        assert role_name == "master", "unknown role-name " + str(role_name)
        assert role_idx == "0", "unknown role-idx " + str(role_idx)


@utils.case()
def test_kill_job_with_message(args):
    job_spec = utils.gen_default_job_description("regular", args.email,
                                                 args.uid, args.vc)

    with utils.run_job(args.rest, job_spec) as job:
        state = job.block_until_state_not_in(
            {"unapproved", "queued", "scheduling"})
        assert state == "running"
        expected = "dummy"

        utils.kill_job(args.rest, args.email, job.jid, expected)

        state = job.block_until_state_not_in({"running", "killing"}, timeout=30)
        assert state == "killed"

        details = utils.get_job_detail(args.rest, args.email, job.jid)
        message = details.get("errorMsg")
        assert message == expected, "unexpected message " + message
