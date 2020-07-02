#!/usr/bin/env python3

import argparse
import datetime
import dateutil.parser
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
        return output, 0
    except subprocess.TimeoutExpired:
        logger.warning("%s timeout", command)
    except subprocess.CalledProcessError as e:
        logger.warning("%s returns %s, output %s", command, e.returncode,
                       e.output)
        return e.output, e.returncode
    except Exception:
        logger.exception("%s failed", command)
    return None, 1


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

    def get_allow_records(self):
        args = urllib.parse.urlencode({
            "userName": "Administrator",
            "user": "all",
        })
        url = urllib.parse.urljoin(self.rest_url, "/AllowRecord") + "?" + args
        resp = requests.get(url, timeout=10)
        return resp

    def add_allow_record(self, user, ip):
        args = urllib.parse.urlencode({
            "userName": "Administrator",
            "user": user,
            "ip": ip,
        })
        url = urllib.parse.urljoin(self.rest_url, "/AllowRecord") + "?" + args
        resp = requests.post(url, timeout=10)
        return resp

    def delete_allow_record(self, user):
        args = urllib.parse.urlencode({
            "userName": "Administrator",
            "user": user,
        })
        url = urllib.parse.urljoin(self.rest_url, "/AllowRecord") + "?" + args
        resp = requests.delete(url, timeout=10)
        return resp


def remove_expired_records(rest_util):
    resp = rest_util.get_allow_records()
    resp.raise_for_status()
    records = resp.json()

    now = datetime.datetime.utcnow()
    for record in records:
        valid_util = dateutil.parser.parse(record["valid_util"])
        if valid_util < now:
            resp = rest_util.delete_allow_record(record["user"])
            if resp.status_code != 200:
                logger.error("failed to delete expired allow record %s",
                             record)
            else:
                logger.info("deleted expired allow record %s", record)


def get_desired_allow_ips(rest_util):
    resp = rest_util.get_allow_records()
    resp.raise_for_status()
    records = resp.json()
    return [record["ip"] for record in records]


def get_current_allow_ips(az_util):
    return []


def update_allow_ips(desired_ips, current_ips, az_util):
    if set(desired_ips) != set(current_ips):
        logger.info("updating from current ips %s to desired ips %s")
    else:
        logger.info("current ips matches desired ips: %s", desired_ips)


def main(params):
    config = get_config(params.config)
    az_util = AzUtil(config)
    rest_util = RestUtil(config)

    while True:
        try:
            # Remove expired records
            remove_expired_records(rest_util)

            # Get desired allow ips
            desired_ips = get_desired_allow_ips(rest_util)

            # Get current allow records
            current_ips = get_current_allow_ips(az_util)

            # Make changes if necessary
            update_allow_ips(desired_ips, current_ips, az_util)
        except:
            logger.exception("failed to process one run")

        time.sleep(60)


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
