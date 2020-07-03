#!/usr/bin/env python3

import argparse
import datetime
import dateutil.parser
import json
import logging
import os
import pytz
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
                                         timeout=600).decode("utf-8")
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

    def __repr__(self):
        return str(self.__dict__)

    def is_valid(self):
        for _, v in self.__dict__.items():
            if v is None:
                return False
        return True

    def login(self):
        cmd = [
            "az", "login", "--service-principal",
            "-u", "%s" % self.client_id,
            "-p", "%s" % self.password,
            "--tenant", "%s" % self.tenant_id,
        ]
        return exec_cmd(cmd)

    def create_allow_list(self, ips):
        # TODO: Decouple port 30000-49999 and priority from code
        cmd = [
            "az", "network", "nsg", "rule", "create",
            "--subscription", "%s" % self.subscription,
            "--resource-group", "%s" % self.resource_group,
            "--nsg-name", "%s" % self.nsg_name,
            "--name", "allowlist",
            "--protocol", "Tcp",
            "--access", "Allow",
            "--priority", "4000",
            "--destination-port-ranges", "30000-49999",
            "--source-address-prefixes",
        ] + ips
        return exec_cmd(cmd)

    def get_allow_list(self):
        cmd = [
            "az", "network", "nsg", "rule", "show",
            "--subscription", "%s" % self.subscription,
            "--resource-group", "%s" % self.resource_group,
            "--nsg-name", "%s" % self.nsg_name,
            "--name", "allowlist",
        ]
        return exec_cmd(cmd)

    def update_allow_list(self, ips):
        cmd = [
            "az", "network", "nsg", "rule", "update",
            "--subscription", "%s" % self.subscription,
            "--resource-group", "%s" % self.resource_group,
            "--nsg-name", "%s" % self.nsg_name,
            "--name", "allowlist",
            "--source-address-prefixes",
        ] + ips
        return exec_cmd(cmd)

    def delete_allow_list(self):
        cmd = [
            "az", "network", "nsg", "rule", "delete",
            "--subscription", "%s" % self.subscription,
            "--resource-group", "%s" % self.resource_group,
            "--nsg-name", "%s" % self.nsg_name,
            "--name", "allowlist",
        ]
        return exec_cmd(cmd)


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

    now = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)
    for record in records:
        valid_until = dateutil.parser.parse(record["valid_until"])
        if valid_until < now:
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
    resp, code = az_util.get_allow_list()
    if code == 0:
        data = json.loads(resp)
        ips = []

        source = data.get("sourceAddressPrefix")
        if source is not None and source != "":
            ips.append(source)

        sources = data.get("sourceAddressPrefixes")
        if sources is not None:
            ips += sources

        return [ip.split("/")[0] for ip in ips]
    else:
        return []


def update_allow_ips(desired_ips, current_ips, az_util):
    desired_ips = set(desired_ips)
    current_ips = set(current_ips)
    if desired_ips != current_ips:
        if len(desired_ips) == 0:
            resp, code = az_util.delete_allow_list()
        else:
            ips = ["%s/32" % ip for ip in list(desired_ips)]
            if len(current_ips) == 0:
                resp, code = az_util.create_allow_list(ips)
            else:
                resp, code = az_util.update_allow_list(ips)

        if code == 0:
            logger.info("updated from current ips %s to desired ips %s",
                        list(current_ips), list(desired_ips))
        else:
            logger.error("failed to update from current ips %s to desired ips "
                         "%s. resp: %s",
                         list(current_ips), list(desired_ips), resp)
    else:
        logger.info("current ips matches desired ips: %s", list(desired_ips))


def main(params):
    # Check permission
    while True:
        try:
            config = get_config(params.config)
            az_util = AzUtil(config)

            if not az_util.is_valid():
                raise ValueError("invalid az util %s" % az_util)

            resp, code = az_util.login()
            try:
                subscriptions = [obj["name"] for obj in json.loads(resp)]
            except:
                subscriptions = []
            if code != 0:
                raise RuntimeError("failed to login. %s" % az_util)
            elif az_util.subscription not in subscriptions:
                raise RuntimeError("no permission to subscription %s" % az_util)
            else:
                logger.info("%s has permission to subscription '%s'",
                            az_util.client_id, az_util.subscription)
                break
        except Exception as e:
            logger.error("incorrect AZ setup. sleep for 1 day. %s", str(e))
            time.sleep(86400)

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
