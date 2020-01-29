#!/usr/bin/python

import argparse
import logging
import mysql.connector
import json
import base64
import yaml

log = logging.getLogger(__name__)

def get_images(username, password, host, database):
    result = []

    conn = mysql.connector.connect(user=username, password=password,
            host=host, database=database)
    cursor = conn.cursor()
    sql = "SELECT jobId, jobParams FROM jobs"
    cursor.execute(sql)
    data = cursor.fetchall()
    for id, params in data:
        params = json.loads(base64.b64decode(params))
        result.append(params["image"])
    conn.close()
    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", "-c", help="path to config.yaml", required=True)
    parser.add_argument("--cluster", "-i", help="path to clusterID.yml", required=True)
    args = parser.parse_args()

    logging.basicConfig(format="%(asctime)s - %(levelname)s - %(filename)s:%(lineno)s - %(message)s",
            level=logging.INFO)

    with open("config.yaml") as f:
        mysql_config = yaml.load(f)

    with open("deploy/clusterID.yml") as f:
        cluster_id = yaml.load(f)["clusterId"]

    images = get_images(mysql_config["mysql_username"], mysql_config["mysql_password"],
        mysql_config["mysql_node"], "DLWSCluster-" + cluster_id)
    for i in images:
        print(i)
