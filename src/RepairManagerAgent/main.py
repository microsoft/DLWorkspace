import requests
import time
import yaml
import logging
import logging.config
import os

with open('./logging.yaml', 'r') as log_file:
    log_config = yaml.safe_load(log_file)

logging.config.dictConfig(log_config)
logger = logging.getLogger(__name__)

def reboot_node():
    os.system('sync')
    os.system('reboot -f')

def Run():
    etcd_server = os.environ["ETCD_SERVER"]
    etcd_port = os.environ["ETCD_PORT"]
    node_name = os.environ["NODE_NAME"]
    key = f'{node_name}/reboot'
    etcd_url = f'http://{etcd_server}:{etcd_port}/v2/keys/{key}'
    logger.debug(etcd_url)

    while True:
        try: 
            response = requests.get(etcd_url, timeout=5)
            r_json = response.json()

            if r_json is not None:
                logger.debug(r_json)

                if 'node' in r_json and \
                r_json['node']['key'] == f'/{key}' and \
                r_json['node']['value'] == 'True':
                    # delete the key before attempting to reboot
                    requests.delete(etcd_url)
                    logger.warning("!!!Attempting to reboot the node!!!")
                    reboot_node()
        except:
            logger.exception(f'Error retrieving data from {etcd_url}')

        time.sleep(5)


if __name__ == '__main__':
    Run()
