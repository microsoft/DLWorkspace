#!/usr/bin/env python3

import argparse
import logging
import logging.config
import os
import sys
import time
import yaml


from cluster_manager import setup_exporter_thread, \
    manager_iteration_histogram, \
    register_stack_trace_dump, \
    update_file_modification_time

sys.path.append(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "../utils"))

from DataHandler import DataHandler

DAYS_AGO = 1
logger = logging.getLogger(__name__)


def create_log(logdir='/var/log/dlworkspace'):
    if not os.path.exists(logdir):
        os.system("mkdir -p " + logdir)

    with open('logging.yaml') as f:
        logging_config = yaml.full_load(f)

    log_filename = os.path.join(logdir, "db_manager.log")
    logging_config["handlers"]["file"]["filename"] = log_filename
    logging.config.dictConfig(logging_config)


def delete_old_cluster_status():
    table = "clusterstatus"
    with DataHandler() as data_handler:
        num_rows = data_handler.count_rows(table)
        if num_rows <= 10: # Retain 10 rows for safety
            return

        logger.info("Deleting rows from table %s older than %s day(s)", table,
                    DAYS_AGO)
        ret = data_handler.delete_rows_from_table_older_than_days(
            table, DAYS_AGO)
        ret_status = "succeeded" if ret is True else "failed"
        logger.info("Deleting rows from table %s older than %s day(s) %s",
                    table, DAYS_AGO, ret_status)


def run():
    register_stack_trace_dump()
    create_log()
    while True:
        update_file_modification_time("db_manager")

        with manager_iteration_histogram.labels("db_manager").time():
            try:
                delete_old_cluster_status()
            except:
                logger.exception("Deleting old cluster status failed",
                                 exc_info=True)
        time.sleep(86400)


if __name__ == '__main__':
    # TODO: This can be made as a separate service to GC DB and orphaned pods
    parser = argparse.ArgumentParser()
    parser.add_argument("--port",
                        "-p",
                        help="port of exporter",
                        type=int,
                        default=9209)
    args = parser.parse_args()
    setup_exporter_thread(args.port)

    run()
