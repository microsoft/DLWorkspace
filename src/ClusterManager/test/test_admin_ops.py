#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging

import utils

logger = logging.getLogger(__file__)


@utils.case(dangerous=True)
def test_vc_quota_change(args):
    job_spec = utils.gen_default_job_description("regular", args.email,
                                                 args.uid, args.vc)

    with utils.vc_setting(args.rest, args.vc, args.email,
                          {"job_max_time_second": 5}):
        with utils.run_job(args.rest, job_spec) as job:
            state = job.block_until_state_not_in(
                {"unapproved", "queued", "scheduling"})
            assert state == "running"

            state = job.block_until_state_not_in({"running"}, timeout=30)
            assert state == "killed"
            expected = "running exceed pre-defined 5s"

            details = utils.get_job_detail(args.rest, args.email, job.jid)
            message = details.get("errorMsg")
            assert message == expected, "unexpected message " + message