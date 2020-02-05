#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import logging
import time

import utils

logger = logging.getLogger(__file__)


def test_regular_job_running(args):
    logger.info("test_regular_job_running ...")

    expected = "wantThisInLog"
    cmd = "echo %s ; sleep 1800" % expected

    image = "indexserveregistry.azurecr.io/deepscale:1.0.post0"
    with utils.run_job(args.rest, "regular", args.email, args.uid, args.vc,
                       image, cmd) as job:
        state = utils.block_until_state_not_in(
            args.rest, job.jid, {"unapproved", "queued", "scheduling"})
        assert state == "running"

        for _ in range(10):
            log = utils.get_job_log(args.rest, args.email, job.jid)

            if expected not in log["log"]:
                time.sleep(0.5)
        assert expected in log["log"]


def test_distributed_job_running(args):
    logger.info("test_distributed_job_running ...")

    expected = "wantThisInLog"
    cmd = "echo %s ; sleep 1800" % expected

    image = "indexserveregistry.azurecr.io/deepscale:1.0.post0"
    with utils.run_job(args.rest, "distributed", args.email, args.uid, args.vc,
                       image, cmd) as job:
        state = utils.block_until_state_not_in(
            args.rest, job.jid, {"unapproved", "queued", "scheduling"})
        assert state == "running"

        for _ in range(10):
            log = utils.get_job_log(args.rest, args.email, job.jid)

            if expected not in log["log"]:
                time.sleep(0.5)
        assert expected in log["log"]


def test_data_job_running(args):
    logger.info("test_data_job_running ...")

    expected_state = "finished"
    expected_word = "wantThisInLog"
    cmd = "mkdir -p /tmp/dlts_test_dir; " \
          "echo %s > /tmp/dlts_test_dir/testfile; " \
          "cd /DataUtils; " \
          "./copy_data.sh /tmp/dlts_test_dir adl://indexserveplatform-experiment-c09.azuredatalakestore.net/local/dlts_test_dir True 4194304 4 2; " \
          "./copy_data.sh adl://indexserveplatform-experiment-c09.azuredatalakestore.net/local/dlts_test_dir /tmp/dlts_test_dir_copyback False 33554432 4 2; " \
          "cat /tmp/dlts_test_dir_copyback/testfile; " % expected_word

    image = "indexserveregistry.azurecr.io/dlts-data-transfer-image:latest"
    with utils.run_job(args.rest, "data", args.email, args.uid, args.vc, image,
                       cmd) as job:
        state = utils.block_until_state_not_in(
            args.rest, job.jid,
            {"unapproved", "queued", "scheduling", "running"})
        assert expected_state == state

        log = utils.get_job_log(args.rest, args.email, job.jid)
        assert expected_word in log["log"]


def test_job_fail(args):
    logger.info("test_job_fail ...")

    expected_state = "failed"
    cmd = "false"

    image = "indexserveregistry.azurecr.io/deepscale:1.0.post0"
    with utils.run_job(args.rest, "regular", args.email, args.uid, args.vc,
                       image, cmd) as job:
        state = utils.block_until_state_not_in(
            args.rest, job.jid,
            {"unapproved", "queued", "scheduling", "running"})
        assert expected_state == state


def test_op_job(args):
    logger.info("test_op_job ...")

    cmd = "sleep 1800"
    image = "indexserveregistry.azurecr.io/deepscale:1.0.post0"
    job_id = utils.post_regular_job(args.rest, args.email, args.uid,
                                    args.vc, image, cmd)
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
    assert "Success, the job is scheduled to be terminated." == resp["result"]

    state = utils.block_until_state_not_in(args.rest, job_id, {"killing"})
    assert "killed" == state


def test_batch_op_jobs(args):
    logger.info("test_batch_op_jobs ...")

    cmd = "sleep 1800"
    image = "indexserveregistry.azurecr.io/deepscale:1.0.post0"
    num_jobs = 2
    job_ids = []
    for i in range(num_jobs):
        job_id = utils.post_regular_job(args.rest, args.email, args.uid,
                                        args.vc, image, cmd)
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


def main(args):
    test_regular_job_running(args)
    test_distributed_job_running(args)
    test_data_job_running(args)
    test_job_fail(args)
    test_op_job(args)
    test_batch_op_jobs(args)


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s',
                        level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument("--rest",
                        "-r",
                        required=True,
                        help="rest api url, http://localhost:5000")
    parser.add_argument("--vc", "-v", required=True, help="vc to submit job")
    parser.add_argument("--email",
                        "-e",
                        required=True,
                        help="email to submit job to rest")
    parser.add_argument("--uid",
                        "-u",
                        required=True,
                        help="uid to submit job to rest")
    #parser.add_argument("--jid", "-j", required=True, help="job_id to query")
    #parser.add_argument("--k8s", "-l", required=True, help="kubernetes api uri eg. http://10.151.40.133:143")
    #parser.add_argument("--config", "-i", required=True, help="path to config dir")
    args = parser.parse_args()

    main(args)
