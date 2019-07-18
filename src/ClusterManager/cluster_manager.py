import yaml
import subprocess32
import os
import logging
import logging.config
import sys
import time

logger = logging.getLogger(__name__)

def create_log(logdir="/var/log/dlworkspace"):
    if not os.path.exists(logdir):
        os.system("mkdir -p " + logdir)
    with open("logging.yaml") as f:
        logging_config = yaml.load(f)
    logging_config["handlers"]["file"]["filename"] = logdir+"/clustermanager.log"
    logging.config.dictConfig(logging_config)


def Run():
    create_log()

    cwd = os.path.dirname(__file__)
    cmds = [
            ["python", os.path.join(cwd, "job_manager.py")],
            ["python", os.path.join(cwd, "user_manager.py")],
            ["python", os.path.join(cwd, "node_manager.py")],
            ["python", os.path.join(cwd, "joblog_manager.py")],
            ["python", os.path.join(cwd, "command_manager.py")],
            ["python", os.path.join(cwd, "endpoint_manager.py")],
            ]

    FNULL = open(os.devnull, "w")

    childs = [None] * len(cmds)

    while True:
        for i, cmd in enumerate(cmds):
            child = childs[i]
            if child is None or child.poll() is not None:
                if child is not None:
                    logger.info("%s is dead restart it", cmd)
                try:
                    childs[i] = subprocess32.Popen(cmd,
                            stdin=FNULL, close_fds=True)
                except Exception as e:
                    logger.exception("caught exception when trying to start %s, ignore",
                            cmd)
        time.sleep(60)

if __name__ == "__main__":
    sys.exit(Run())
