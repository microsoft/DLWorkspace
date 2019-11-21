import faulthandler
import os
import sys
import yaml
import signal
import logging


sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../utils"))
from config import config
from logging.config import dictConfig
from DataHandler import DataHandler
from storage_manager import StorageManager

LOGGING_FILE = "logging.yaml"


dir_path = os.path.dirname(os.path.realpath(__file__))
with open(os.path.join(dir_path, LOGGING_FILE), "r") as f:
    logging_config = yaml.safe_load(f)
    dictConfig(logging_config)
logger = logging.getLogger(__name__)


def register_stack_trace_dump():
    faulthandler.register(signal.SIGTRAP, all_threads=True, chain=False)


def main():
    while True:
        sm_config = config.get("storage_monitor", None)
        if sm_config is None or sm_config.get("enabled", False) is False:
            logger.info("storage_monitor is not enabled.")
            sys.exit(0)

        sm = StorageManager(sm_config)
        try:
            sm.run()
        except Exception as e:
            logger.error("StorageManager.run failed with exception %s" % str(e))


if __name__ == "__main__":
    register_stack_trace_dump()
    main()
