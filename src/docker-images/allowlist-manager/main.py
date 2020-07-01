#!/usr/bin/env python3

import argparse
import logging
import os
import requests
import subprocess
import time
import urllib.parse
import yaml

from logging import handlers

logger = logging.getLogger(__name__)


def get_config(config_path):
    with open(os.path.join(config_path, "config.yaml"), "r") as f:
        config = yaml.safe_load(f)
    return config


def exec_cmd(command):
    try:
        output = subprocess.check_output(command, stderr=subprocess.STDOUT,
                                         timeout=10).decode("utf-8")
        logger.debug("%s output: %s", command, output)
        return output
    except subprocess.TimeoutExpired:
        logger.warning("%s timeout", command)
    except subprocess.CalledProcessError as e:
        logger.warning("%s returns %d, output %s", e.returncode, e.output)
    except Exception:
        logger.exception("%s failed")
    return None


class AzUtil(object):
    def __init__(self, config):
        self.subscription = config.get("subscription")
        self.resource_group = config.get("resource_group")
        self.nsg_name = config.get("nsg_name")

        self.tenant_id = config.get("tenant_id")
        self.client_id = config.get("client_id")
        self.password = config.get("password")

        self.is_logged_in = False

    def login(self):
        cmd = "az login --service-principal -u %s -p %s --tenant %s" % (
            self.client_id, self.password, self.tenant_id)

    def create_allowlist(self, ips):
        cmd = """
            az network nsg rule create \
                --subscription %s \
                --resource-group %s \
                --nsg-name %s \
                --name allowlist \
                --protocol Tcp \
                --priority 30000 \
                --destination-port-ranges 30000-49999 \
                --source-address-prefixes %s \
                --access Allow
        """ % (self.subscription,
               self.resource_group,
               self.nsg_name,
               ips)

    def get_allowlist(self):
        cmd = """
            az network nsg rule show \
                --subscription %s \
                --resource-group %s \
                --nsg-name %s \
                --name allowlist
        """ % (self.subscription,
               self.resource_group,
               self.nsg_name)

    def update_allowlist(self, ips):
        cmd = """
            az network nsg rule show \
                --subscription %s \
                --resource-group %s \
                --nsg-name %s \
                --name allowlist \
                --source-address-prefixes %s
        """ % (self.subscription,
               self.resource_group,
               self.nsg_name,
               ips)


class RestUtil(object):
    def __init__(self, config):
        self.rest_url = config.get("rest_url", "http://localhost:5000")

    def get_allowlist(self):
        args = urllib.parse.urlencode({"userName": "Administrator"})
        url = urllib.parse.urljoin(self.rest_url, "/AllowList") + "?" + args
        resp = requests.get(url, timeout=5)
        return resp.json()


def main(params):
    config = get_config(params.config)
    util = AzUtil(config)

    util.login()

    while True:
        if not util.is_logged_in:
            logger.error(" %s", config)
            time.sleep(86400)  # Sleep for 1 day
        try:
            config = get_config(params.config)
        except Exception:
            logger.exception("failed to run")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config",
                        "-c",
                        help="directory path containing config.yaml",
                        default="/etc/allowlist-manager")
    parser.add_argument("--log",
                        "-l",
                        help="log dir to store log",
                        default="/var/log/allowlist-manager")
    parser.add_argument("--interval",
                        "-i",
                        help="interval in seconds between each run",
                        default=60)
    args = parser.parse_args()

    console_handler = logging.StreamHandler()
    file_handler = handlers.RotatingFileHandler(
        os.path.join(args.log, "allowlist-manager.log"),
        maxBytes=10240000, backupCount=10)
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(threadName)s - %(filename)s:%(lineno)s - %(message)s",
        level=logging.INFO,
        handlers=[console_handler, file_handler])

    main(args)
