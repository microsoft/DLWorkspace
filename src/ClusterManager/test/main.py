#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import logging
import glob
import datetime
import sys
import copy

import utils

logger = logging.getLogger(__file__)


def should_run(model_name, case_name, full_name, targets):
    if len(targets) == 0:
        return True

    bucket = {model_name, case_name, full_name}

    for target_name in targets:
        if target_name == "":
            continue
        if target_name in bucket:
            return True
    return False


def pick_unfinished_failed_case(case_names, result):
    unfinished = []
    failed = []

    for i, case_name in enumerate(case_names):
        if result[i] is False:
            continue
        elif result[i] is True:
            failed.append(case_name)
        elif result[i] is None:
            unfinished.append(case_name)
        else:
            logger.warning("unknown return value for case %s", case_name)
    return unfinished, failed


def main(args):
    start = datetime.datetime.now()

    f_names = glob.glob("*.py")

    if args.case == "":
        targets = []
    else:
        targets = args.case.split(",")

    normal_cases = []
    normal_case_names = []

    dangerouse_cases = []
    dangerouse_case_names = []

    for name in f_names:
        model_name = name[:-3]
        model = __import__(model_name)

        for obj_name in dir(model):
            obj = getattr(model, obj_name)
            if not hasattr(obj, "is_case"):
                continue
            if not getattr(obj, "is_case"):
                continue

            full_name = model_name + "." + obj_name

            if not should_run(model_name, obj_name, full_name, targets):
                continue

            if getattr(obj, "is_dangerous_case"):
                dangerouse_cases.append(obj)
                dangerouse_case_names.append(full_name)
            else:
                normal_cases.append(obj)
                normal_case_names.append(full_name)

    logger.info("will run %d normal cases %s %s times", len(normal_case_names),
                normal_case_names, args.nums)
    if not args.dangerous:
        logger.info("skip run %d dangerous cases %s",
                    len(dangerouse_case_names), ",".join(dangerouse_case_names))
    else:
        logger.info("will run %d dangerous cases %s",
                    len(dangerouse_case_names), dangerouse_case_names)

    if args.nums > 1:
        cp = copy.deepcopy(normal_cases)
        name_cp = copy.deepcopy(normal_case_names)
        for i in range(args.nums):
            normal_cases.extend(cp)
            normal_case_names.extend(name_cp)
    num_proc = min(args.process, len(normal_cases))

    all_case_names = copy.deepcopy(normal_case_names)

    result = utils.run_cases_in_parallel(normal_cases, args, num_proc)

    if args.dangerous:
        # dangerous case usually involve change vc settings, so run them in sequential
        all_case_names.extend(dangerouse_case_names)
        result.extend(utils.run_cases_in_parallel(dangerouse_cases, args, 1))

    unfinished, failed = pick_unfinished_failed_case(all_case_names, result)

    logger.info("spent %s in executing %d cases %s",
                datetime.datetime.now() - start, len(all_case_names),
                all_case_names)

    logger.info("%d failed %s", len(failed), ",".join(failed))
    logger.info("%d unfinished %s", len(unfinished), ",".join(unfinished))

    if len(failed) + len(unfinished) > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    logging.basicConfig(
        format=
        "%(asctime)s: %(levelname)s - %(filename)s:%(lineno)d@%(process)d: %(message)s",
        level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--process",
                        "-p",
                        default=10,
                        type=int,
                        help="how many process used to run cases")
    parser.add_argument("--case",
                        "-a",
                        default="",
                        help="which case(s) to run, comma seperated")
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
    parser.add_argument("--config",
                        "-c",
                        required=True,
                        help="path to config dir")
    parser.add_argument("--nums",
                        "-n",
                        type=int,
                        default=1,
                        help="number of times to test all cases")
    parser.add_argument(
        "--dangerous",
        "-d",
        action="store_true",
        help="run dangerous cases or not, these cases will change settings")
    args = parser.parse_args()

    main(args)
