import requests
import logging
import commands

def check_for_reboot_signal(etcd_url, node_name):
    key = f'{node_name}/reboot'
    reboot_url = f'{etcd_url}/{key}'

    try:
        response = requests.get(reboot_url, timeout=5)
        r_json = response.json()

        if r_json is not None:
            logging.debug(r_json)

        if 'node' in r_json and \
            r_json['node']['key'] == f'/{key}':

            value = r_json['node']['value']

            if value == 'True':
                # delete the key before attempting to reboot
                requests.delete(reboot_url)
                logging.warning("!!!Rebooting the node!!!")
                commands.reboot_node()

            if value == 'DryRun':
                requests.delete(reboot_url)
                logging.warning("Dry-Run request to reboot the node received")

    except:
        logging.exception(f'Error retrieving data from {reboot_url}')

