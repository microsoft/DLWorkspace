import faulthandler
import os
import sys
import yaml
import signal
import logging

from logging.config import dictConfig
from storage_manager import StorageManager

LOGGING_FILE = "logging.yaml"
CONFIG_FILE = "config.yaml"


dir_path = os.path.dirname(os.path.realpath(__file__))
with open(os.path.join(dir_path, LOGGING_FILE), "r") as f:
    logging_config = yaml.safe_load(f)
    dictConfig(logging_config)
logger = logging.getLogger(__name__)


with open(os.path.join(dir_path, CONFIG_FILE), "r") as f:
    config = yaml.safe_load(f)


def register_stack_trace_dump():
    faulthandler.register(signal.SIGTRAP, all_threads=True, chain=False)


def main():
    while True:
        sm_config = config.get("storage_manager", None)
        if sm_config is None:
            logger.info("storage_manager is not enabled. Exiting ...")
            sys.exit(0)

        smtp = config.get("smtp", None)
        cluster_name = config.get("cluster_name_friendly", None)

        sm = StorageManager(sm_config, smtp, cluster_name)
        try:
            sm.run()
        except Exception as e:
            logger.error("StorageManager.run failed with exception %s", e)


if __name__ == "__main__":
    register_stack_trace_dump()
    main()
