import yaml
import subprocess32
import os
import logging
import logging.config
import sys
import time
import argparse
import threading

from prometheus_client.twisted import MetricsResource

from twisted.web.server import Site
from twisted.web.resource import Resource
from twisted.internet import reactor

logger = logging.getLogger(__name__)


class HealthResource(Resource):
    def render_GET(self, request):
        request.setHeader("Content-Type", "text/html; charset=utf-8")
        return "<html>Ok</html>".encode("utf-8")

def exporter_thread(port):
    root = Resource()
    root.putChild(b"metrics", MetricsResource())
    root.putChild(b"healthz", HealthResource())
    factory = Site(root)
    reactor.listenTCP(port, factory)
    reactor.run()

def setup_exporter_thread(port):
    t = threading.Thread(target=exporter_thread, args=(port,),
            name="exporter")
    t.start()
    return t

def create_log(logdir="/var/log/dlworkspace"):
    if not os.path.exists(logdir):
        os.system("mkdir -p " + logdir)
    with open("logging.yaml") as f:
        logging_config = yaml.load(f)
    logging_config["handlers"]["file"]["filename"] = logdir + "/clustermanager.log"
    logging.config.dictConfig(logging_config)


def Run(args):
    create_log()

    cwd = os.path.dirname(__file__)
    cmds = [
        ["python", os.path.join(cwd, "job_manager.py"), args.j],
        ["python", os.path.join(cwd, "user_manager.py"), args.u],
        ["python", os.path.join(cwd, "node_manager.py"), args.n],
        ["python", os.path.join(cwd, "joblog_manager.py"), args.l],
        ["python", os.path.join(cwd, "command_manager.py"), args.c],
        ["python", os.path.join(cwd, "endpoint_manager.py"), args.e],
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
                    childs[i] = subprocess32.Popen(cmd, stdin=FNULL, close_fds=True)
                except Exception as e:
                    logger.exception("caught exception when trying to start %s, ignore", cmd)
        time.sleep(60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-j", help="port of job_manager", type=int, default=9200)
    parser.add_argument("-u", help="port of user_manager", type=int, default=9201)
    parser.add_argument("-n", help="port of node_manager", type=int, default=9202)
    parser.add_argument("-l", help="port of joblog_manager", type=int, default=9203)
    parser.add_argument("-c", help="port of command_manager", type=int, default=9204)
    parser.add_argument("-e", help="port of endpoint_manager", type=int, default=9205)
    args = parser.parse_args()

    sys.exit(Run(args))
