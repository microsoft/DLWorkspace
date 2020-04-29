import time
import yaml
import logging
import logging.config
import os
import etcd_util

with open('./logging.yaml', 'r') as log_file:
    log_config = yaml.safe_load(log_file)

logging.config.dictConfig(log_config)
logger = logging.getLogger(__name__)


def Run():
    etcd_server = os.environ["ETCD_SERVER"]
    etcd_port = os.environ["ETCD_PORT"]
    node_name = os.environ["NODE_NAME"]
    etcd_url = f'http://{etcd_server}:{etcd_port}/v2/keys'
    logger.debug(etcd_url)

    while True:

        etcd_util.check_for_reboot_signal(etcd_url, node_name)

        time.sleep(5)


if __name__ == '__main__':
    Run()
