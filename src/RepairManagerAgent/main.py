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
    while True:
        logger.debug('Polling ETCD...')
        reboot_key = "worker0/reboot"
        etcd_ip = "INSERT_IP_HERE"
        url = f'http://{etcd_ip}:INSERT_PORT_HERE/v2/keys'
        response = requests.get(f'{url}/{reboot_key}')
        r_json = response.json()
        logger.debug(r_json)
        
        if 'node' in r_json and 'key' in r_json['node']:
            value = r_json['node']['value']
            if value == 'True':
                requests.put(f'{url}/{reboot_key}', data={'value':'False'})
                logger.debug("Attempting to reboot the node!")
                #reboot_node()
        else:
            logger.debug(r_json)

        time.sleep(5)

if __name__ == '__main__':
    Run()
