#!/usr/bin/python3

import argparse
import logging
import mysql.connector
import json
import base64
import yaml
import os

log = logging.getLogger(__name__)


def get_images(username, password, host, database):
    result = []

    conn = mysql.connector.connect(user=username,
                                   password=password,
                                   host=host,
                                   database=database)
    cursor = conn.cursor()
    sql = "SELECT jobId, jobParams FROM jobs"
    cursor.execute(sql)
    data = cursor.fetchall()
    for id, params in data:
        params = json.loads(base64.b64decode(params))
        image = params["image"]
        if " " in image:
            continue
        result.append(image)
    conn.close()
    return list(set(result))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config",
                        "-c",
                        help="comma separated path(s) to config dirs",
                        required=True)
    args = parser.parse_args()
    configs = args.config.split(",")

    logging.basicConfig(
        format=
        "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)s - %(message)s",
        level=logging.INFO)
   
    all_images = []
    for config in configs:
        with open(os.path.join(config, "config.yaml")) as f:
            mysql_config = yaml.load(f)

        with open(os.path.join(config, "clusterID/clusterID.yml")) as f:
            cluster_id = yaml.load(f)["clusterId"]

        images = get_images(mysql_config["mysql_username"],
                            mysql_config["mysql_password"],
                            mysql_config["mysql_node"], "DLWSCluster-" + cluster_id)
        all_images.extend(images)

    all_images = list(set(all_images))
    for i in all_images:
        print(i)
