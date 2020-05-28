#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import time
import copy
import re

import utils

logger = logging.getLogger(__file__)


def test_distributed_job_running(args, preemptable=False):
    expected = "wantThisInLog"
    cmd = "echo %s ; sleep 120" % expected

    job_spec = utils.gen_default_job_description("distributed",
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
        assert expected in log, "assert {} in {}".format(expected, log)


@utils.case()
def test_distributed_non_preemptable_job_running(args):
    test_distributed_job_running(args)


@utils.case()
def test_distributed_preemptable_job_running(args):
    test_distributed_job_running(args, True)


@utils.case()
def test_distributed_job_ssh(args):
    job_spec = utils.gen_default_job_description("distributed", args.email,
                                                 args.uid, args.vc)
    with utils.run_job(args.rest, job_spec) as job:
        endpoints = utils.create_endpoint(args.rest, args.email, job.jid,
                                          ["ssh"])
        endpoints_ids = list(endpoints.keys())
        assert len(endpoints_ids) == 2

        state = job.block_until_state_not_in(
            {"unapproved", "queued", "scheduling"})
        assert state == "running"

        for endpoint_id in endpoints_ids:
            ssh_endpoint = utils.wait_endpoint_state(args.rest, args.email,
                                                     job.jid, endpoint_id)
            logger.debug("endpoint_id is %s, endpoints resp is %s", endpoint_id,
                         ssh_endpoint)

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


@utils.case()
def test_distributed_with_default_cmd(args):
    cmd = """
##################################################
# DeepScale 1.0 redirect (Start)
##################################################
set -e

hostname
whoami

# Create DeepScale 1.0 redirect on master node
sudo chmod -R 777 /root && mkdir -p /root/.ssh && rm -f /root/.ssh/config && ln -s ~/.ssh/config /root/.ssh/config && echo "/root/.ssh/config created" && ls -l /root/.ssh
mkdir -p /opt && sudo rm -f /opt/hostfile && sudo ln -s /job/hostfile /opt/hostfile && cat /opt/hostfile

# Create DeepScale 1.0 redirect for all workers
for i in $(seq 0 $(( ${DLWS_NUM_WORKER} - 1 ))); do
    echo "Creating DeepScale 1.0 redirect for worker ${i}"
    ssh worker-${i} "sudo chmod -R 777 /root && mkdir -p /root/.ssh && rm -f /root/.ssh/config && ln -s ~/.ssh/config /root/.ssh/config && echo "/root/.ssh/config created" && ls -l /root/.ssh"
    ssh worker-${i} "mkdir -p /opt && sudo rm -f /opt/hostfile && sudo ln -s /job/hostfile /opt/hostfile && cat /opt/hostfile"
done
##################################################
# DeepScale 1.0 redirect (End)
##################################################

##################################################
# Unlimit memlock (Start)
##################################################
for i in $(seq 0 $(( ${DLWS_NUM_WORKER} - 1 ))); do
    echo "Creating redirect for worker ${i}"
    ssh worker-${i} "sudo bash -c 'echo -e \"*                soft   memlock         unlimited\n*                hard   memlock         unlimited\" | cat >> /etc/security/limits.conf'"
done
##################################################
# Unlimit memlock (End)
##################################################

##################################################
# User command starts here
##################################################
sleep infinity"""
    job_spec = utils.gen_default_job_description("distributed", args.email,
                                                 args.uid, args.vc)
    with utils.run_job(args.rest, job_spec) as job:
        endpoints = utils.create_endpoint(args.rest, args.email, job.jid,
                                          ["ssh"])
        endpoints_ids = list(endpoints.keys())
        assert len(endpoints_ids) == 2

        state = job.block_until_state_not_in(
            {"unapproved", "queued", "scheduling"})
        assert state == "running"

        for endpoint_id in endpoints_ids:
            ssh_endpoint = utils.wait_endpoint_state(args.rest, args.email,
                                                     job.jid, endpoint_id)
            logger.debug("endpoint_id is %s, endpoints resp is %s", endpoint_id,
                         ssh_endpoint)

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


@utils.case()
def test_distributed_job_env(args):
    envs = {
        "DLWS_HOST_NETWORK": "enable",
        "DLTS_HOST_NETWORK": "enable",
        "DLWS_NUM_PS": "1",
        "DLTS_NUM_PS": "1",
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

    job_spec = utils.gen_default_job_description("distributed",
                                                 args.email,
                                                 args.uid,
                                                 args.vc,
                                                 cmd="sleep infinity")
    with utils.run_job(args.rest, job_spec) as job:
        endpoints = utils.create_endpoint(args.rest, args.email, job.jid,
                                          ["ssh"])
        endpoints_ids = list(endpoints.keys())

        state = job.block_until_state_not_in(
            {"unapproved", "queued", "scheduling"})
        assert state == "running"
        envs["DLWS_JOB_ID"] = job.jid
        envs["DLTS_JOB_ID"] = job.jid

        for endpoint_id in endpoints_ids:
            ssh_endpoint = utils.wait_endpoint_state(args.rest, args.email,
                                                     job.jid, endpoint_id)
            logger.debug("endpoints resp is %s", ssh_endpoint)

            ssh_host = "%s.%s" % (ssh_endpoint["nodeName"],
                                  ssh_endpoint["domain"])
            ssh_port = ssh_endpoint["port"]
            ssh_id = ssh_endpoint["id"]

            role_idx = ssh_id.split("-")[-2]
            match = re.match("([a-z]+)([0-9]+)", role_idx)
            assert match is not None, "%s is not role index name" % (role_idx)

            role, idx = match.groups()

            envs["DLWS_ROLE_NAME"] = role
            envs["DLTS_ROLE_NAME"] = role
            envs["DLWS_ROLE_IDX"] = idx
            envs["DLTS_ROLE_IDX"] = idx

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
                                               job_manager_pod_name,
                                               "jobmanager", ssh_cmd)

            logger.debug("cmd %s code is %s, output is %s", " ".join(ssh_cmd),
                         code, output)

            for key, val in envs.items():
                expected_output = "%s=%s" % (key, val)
                assert output.find(
                    expected_output) != -1, "could not find %s in log %s" % (
                        expected_output, output)


@utils.case()
def test_blobfuse(args):
    job_spec = utils.gen_default_job_description("distributed", args.email,
                                                 args.uid, args.vc)

    job_spec["plugins"] = utils.load_azure_blob_config(args.config, "/tmp/blob")

    with utils.run_job(args.rest, job_spec) as job:
        state = job.block_until_state_not_in(
            {"unapproved", "queued", "scheduling"})
        assert state == "running"

        ps_label = "jobId=%s,jobRole=ps" % job.jid
        pods = utils.kube_get_pods(args.config, "default", ps_label)
        assert len(pods) == 1

        ps_pod_name = pods[0].metadata.name
        ps_container_name = pods[0].spec.containers[0].name
        msg = "this is dummy from ps"
        ps_cmd = ["bash", "-c", "echo %s > /tmp/blob/${DLWS_JOB_ID}" % (msg)]

        code, output = utils.kube_pod_exec(args.config, "default", ps_pod_name,
                                           ps_container_name, ps_cmd)
        assert code == 0, "code is %d, output is %s" % (code, output)

        worker_label = "jobId=%s,jobRole=worker" % job.jid
        pods = utils.kube_get_pods(args.config, "default", worker_label)
        assert len(pods) == 1

        worker_pod_name = pods[0].metadata.name
        worker_container_name = pods[0].spec.containers[0].name
        worker_cmd = [
            "bash", "-c",
            "cat /tmp/blob/${DLWS_JOB_ID} ; rm /tmp/blob/${DLWS_JOB_ID}"
        ]

        code, output = utils.kube_pod_exec(args.config, "default",
                                           worker_pod_name,
                                           worker_container_name, worker_cmd)
        assert code == 0, "code is %d, output is %s" % (code, output)
        assert msg + "\n" == output, "code is %d, output is %s" % (code, output)


# uncomment to run perf case
#@utils.case()
def perf(args):
    cmd = "sleep 30"

    job_spec = utils.gen_default_job_description("distributed",
                                                 args.email,
                                                 args.uid,
                                                 args.vc,
                                                 cmd=cmd)
    for _ in range(10):
        jids = []
        for _ in range(5):
            jids.append(utils.post_job(args.rest, job_spec))

        for jid in jids:
            state = utils.block_until_state_not_in(
                args.rest, jid,
                {"unapproved", "queued", "scheduling", "running"})
            logger.info("%s is in state %s", jid, state)


@utils.case()
def test_ssh_cuda_visible_devices(args):

    job_spec = utils.gen_default_job_description("distributed",
                                                 args.email,
                                                 args.uid,
                                                 args.vc,
                                                 cmd="sleep infinity",
                                                 resourcegpu=4)
    with utils.run_job(args.rest, job_spec) as job:
        endpoints = utils.create_endpoint(args.rest, args.email, job.jid,
                                          ["ssh"])
        endpoints_ids = list(endpoints.keys())

        state = job.block_until_state_not_in(
            {"unapproved", "queued", "scheduling"})
        assert state == "running"

        for endpoint_id in endpoints_ids:
            ssh_endpoint = utils.wait_endpoint_state(args.rest, args.email,
                                                     job.jid, endpoint_id)
            logger.debug("endpoints resp is %s", ssh_endpoint)

            ssh_host = "%s.%s" % (ssh_endpoint["nodeName"],
                                  ssh_endpoint["domain"])
            ssh_port = ssh_endpoint["port"]
            ssh_id = ssh_endpoint["id"]

            role_idx = ssh_id.split("-")[-2]
            match = re.match("([a-z]+)([0-9]+)", role_idx)
            assert match is not None, "%s is not role index name" % role_idx

            role, idx = match.groups()

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
                "echo a; env | grep CUDA_VISIBLE_DEVICES;",
                "grep CUDA_VISIBLE_DEVICES ~/.ssh/environment; echo b",
            ]

            code, output = utils.kube_pod_exec(args.config, "default",
                                               job_manager_pod_name,
                                               "jobmanager", ssh_cmd)

            logger.debug("cmd %s code is %s, output is %s", " ".join(ssh_cmd),
                         code, output)

            if role == "ps":
                expected = "a\nb"
            else:
                expected = "a\nCUDA_VISIBLE_DEVICES=0,1,2,3\nCUDA_VISIBLE_DEVICES=0,1,2,3\nb"

            assert expected in output, "could not find %s in output %s" % (
                expected, output)


@utils.case()
def test_job_directory(args):
    """ assert user should be able to write to /job and contents are shared """
    job_spec = utils.gen_default_job_description("distributed", args.email,
                                                 args.uid, args.vc)

    with utils.run_job(args.rest, job_spec) as job:
        state = job.block_until_state_not_in(
            {"unapproved", "queued", "scheduling"})
        assert state == "running"

        ps_label = "jobId=%s,jobRole=ps" % job.jid
        pods = utils.kube_get_pods(args.config, "default", ps_label)
        assert len(pods) == 1

        ps_pod_name = pods[0].metadata.name
        ps_container_name = pods[0].spec.containers[0].name
        msg = "this is dummy from ps"
        ps_cmd = ["bash", "-c", "echo %s > /job/${DLWS_JOB_ID}" % (msg)]

        code, output = utils.kube_pod_exec(args.config, "default", ps_pod_name,
                                           ps_container_name, ps_cmd)
        assert code == 0, "code is %d, output is %s" % (code, output)

        worker_label = "jobId=%s,jobRole=worker" % job.jid
        pods = utils.kube_get_pods(args.config, "default", worker_label)
        assert len(pods) == 1

        worker_pod_name = pods[0].metadata.name
        worker_container_name = pods[0].spec.containers[0].name
        worker_cmd = [
            "bash", "-c", "cat /job/${DLWS_JOB_ID} ; rm /job/${DLWS_JOB_ID}"
        ]

        code, output = utils.kube_pod_exec(args.config, "default",
                                           worker_pod_name,
                                           worker_container_name, worker_cmd)
        assert code == 0, "code is %d, output is %s" % (code, output)
        assert msg + "\n" == output, "code is %d, output is %s" % (code, output)


@utils.case()
def test_fault_tolerance(args):
    # Job is only retried when launcher is controller.
    if utils.get_launcher(args.config) == "python":
        return

    job_spec = utils.gen_default_job_description("distributed", args.email,
                                                 args.uid, args.vc)

    with utils.run_job(args.rest, job_spec) as job:
        endpoints = utils.create_endpoint(args.rest, args.email, job.jid,
                                          ["ssh"])
        endpoints_ids = list(endpoints.keys())
        assert len(endpoints_ids) == 2
        endpoint_id = endpoints_ids[0]

        state = job.block_until_state_not_in(
            {"unapproved", "queued", "scheduling"})
        assert state == "running"

        ssh_endpoint = utils.wait_endpoint_state(args.rest, args.email, job.jid,
                                                 endpoint_id)
        ssh_host = "%s.%s" % (ssh_endpoint["nodeName"], ssh_endpoint["domain"])
        ssh_port = ssh_endpoint["port"]

        logger.info("current ssh endpoint is %s:%s", ssh_host, ssh_port)

        pods = utils.kube_get_pods(args.config, "default",
                                   "jobId=%s" % (job.jid))
        for pod in pods:
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


def test_image_pull_msg(args):
    expected = "ImagePullBackOff"

    job_spec = utils.gen_default_job_description("distributed",
                                                 args.email,
                                                 args.uid,
                                                 args.vc,
                                                 image="not_exist_image")
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
def test_distributed_job_mountpoints(args):
    job_spec = utils.gen_default_job_description("distributed", args.email,
                                                 args.uid, args.vc)

    with utils.run_job(args.rest, job_spec) as job:
        state = job.block_until_state_not_in({"unapproved", "queued"})
        assert state in ["scheduling", "running"]

        pods = utils.kube_get_pods(args.config, "default", "jobId=%s" % job.jid)

        mps = utils.load_cluster_nfs_mountpoints(args, job.jid)
        mps.extend(utils.load_system_mountpoints(args))
        mps.extend(utils.load_infiniband_mounts(args))

        for pod in pods:
            for mp in mps:
                assert utils.mountpoint_in_pod(mp, pod), \
                    "mountpoint %s not in distributed job %s" % (mp, job.jid)


@utils.case()
def test_distributed_job_system_envs(args):
    envs = utils.load_distributed_system_envs(args)

    job_spec = utils.gen_default_job_description("distributed",
                                                 args.email,
                                                 args.uid,
                                                 args.vc,
                                                 cmd="sleep infinity")
    with utils.run_job(args.rest, job_spec) as job:
        endpoints = utils.create_endpoint(args.rest, args.email, job.jid,
                                          ["ssh"])
        endpoints_ids = list(endpoints.keys())

        state = job.block_until_state_not_in(
            {"unapproved", "queued", "scheduling"})
        assert state == "running"

        for endpoint_id in endpoints_ids:
            ssh_endpoint = utils.wait_endpoint_state(args.rest, args.email,
                                                     job.jid, endpoint_id)
            logger.debug("endpoints resp is %s", ssh_endpoint)

            ssh_host = "%s.%s" % (ssh_endpoint["nodeName"],
                                  ssh_endpoint["domain"])
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
                                               job_manager_pod_name,
                                               "jobmanager", ssh_cmd)

            logger.debug("cmd %s code is %s, output is %s", " ".join(ssh_cmd),
                         code, output)

            for key, val in envs.items():
                expected_output = "%s=%s" % (key, val)
                assert output.find(
                    expected_output) != -1, "could not find %s in log %s" % (
                        expected_output, output)
