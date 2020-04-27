#!/usr/bin/env python3

import os
import sys
import yaml
import argparse
import logging

import mysql.connector

logger = logging.getLogger(__name__)


def build_mysql_connection(rest_config_path):
    with open(rest_config_path) as f:
        cluster_config = yaml.load(f)

    host = cluster_config["mysql"]["hostname"]
    port = cluster_config["mysql"]["port"]
    username = cluster_config["mysql"]["username"]
    password = cluster_config["mysql"]["password"]
    db_name = "DLWSCluster-%s" % cluster_config["clusterId"]
    return mysql.connector.connect(user=username,
                                   password=password,
                                   host=host,
                                   port=port,
                                   database=db_name)


def alter_table(rest_config_path):
    conn = build_mysql_connection(rest_config_path)
    cursor = conn.cursor()
    cursor.execute(
        "ALTER TABLE identity ADD COLUMN public_key TEXT not null"
    )
    cursor.execute(
        "ALTER TABLE identity ADD COLUMN private_key TEXT not null"
    )
    conn.commit()
    cursor.close()
    conn.close()


def dump_data(rest_config_path, work_path):
    conn = build_mysql_connection(rest_config_path)
    cursor = conn.cursor()
    cursor.execute("SELECT `identityName` FROM identity")
    users = cursor.fetchall()
    for user_name, in users:
        alias = user_name
        if "@" in alias:
            alias = alias.split("@")[0]
        if "/" in alias:
            alias = alias.split("/")[1]
        if "\\" in alias:
            alias = alias.split("\\")[1]
        logger.info("dumping %s", alias)
        private_path = os.path.join(work_path, alias, ".ssh", "id_rsa")
        public_path = os.path.join(work_path, alias, ".ssh",
                                   "id_rsa.pub")
        if not os.path.isfile(private_path) or not os.path.isfile(
                public_path):
            logger.warning("%s or %s not exist, ignore", private_path,
                           public_path)
            continue
        with open(private_path) as f:
            private_key = f.read()
        with open(public_path) as f:
            public_key = f.read()
        cursor.execute(
            """UPDATE identity
                SET private_key = %s, public_key = %s
                WHERE identityName = %s""", (private_key, public_key,
            user_name))
        conn.commit()
    cursor.close()
    conn.close()


def roll_back(rest_config_path):
    conn = build_mysql_connection(rest_config_path)
    cursor = conn.cursor()
    cursor.execute("ALTER TABLE identity DROP COLUMN private_key, DROP COLUMN public_key")
    conn.commit()
    cursor.close()
    conn.close()


def main(action, rest_config_path, work_path):
    if action == "alter":
        alter_table(rest_config_path)
    elif action == "dump":
        dump_data(rest_config_path, work_path)
    elif action == "rollback":
        roll_back(rest_config_path)
    else:
        logger.error("unknown action %s", action)
        sys.exit(2)


if __name__ == '__main__':
    logging.basicConfig(
        format=
        "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)s - %(message)s",
        level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["alter", "dump", "rollback"])
    parser.add_argument("--work_path",
                        help="path to NFS work directory",
                        default="/dlwsdata/work")
    parser.add_argument("--rest_path",
                        help="path to restfulapi config file",
                        default="/etc/RestfulAPI/config.yaml")
    args = parser.parse_args()
    main(args.action, args.rest_path, args.work_path)
