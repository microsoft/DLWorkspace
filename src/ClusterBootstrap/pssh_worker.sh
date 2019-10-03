#!/bin/bash

cmd=$1

CLUSTER_NAME=$(grep cluster_name cluster.yaml | awk '{print $2}' | tr '[:upper:]' '[:lower:]')

grep -B3 "role: worker" cluster.yaml | grep ${CLUSTER_NAME}-worker-  | sed 's/://g' | awk '{print $1}' | grep -v "#" | awk '{printf("%s.%s\n", $1, DOMAIN_SUFFIX)}' DOMAIN_SUFFIX=$(grep domain cluster.yaml | awk '{print $2}') > hostfile

NUM_WORKERS=$(cat hostfile | wc -l)

if [ -z $2 ]; then
    LOG_OPTIONS="-o pssh-log/stdout -e pssh-log/stderr"
else
    LOG_OPTIONS="-i"
fi

parallel-ssh ${LOG_OPTIONS} -t 0 -p ${NUM_WORKERS} -h hostfile -x "-oStrictHostKeyChecking=no -oUserKnownHostsFile=/dev/null -i ./deploy/sshkey/id_rsa" -l core "${cmd}"