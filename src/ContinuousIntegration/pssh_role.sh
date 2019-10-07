#!/bin/bash

role=$1
cmd=$2

CLUSTER_NAME=$(grep cluster_name ../ClusterBootstrap/cluster.yaml | awk '{print $2}' | tr '[:upper:]' '[:lower:]')

if [ ! -e ${role}_list ];then

	grep -B3 "role: ${role}" ../ClusterBootstrap/cluster.yaml | grep ${CLUSTER_NAME}- | sed 's/://g' | awk '{print $1}' | grep -v "#" | awk '{printf("%s.%s\n", $1, DOMAIN_SUFFIX)}' DOMAIN_SUFFIX=$(grep domain ../ClusterBootstrap/cluster.yaml | awk '{print $2}') | sort > ${role}_list

fi;

NUM_roles=$(cat ${role}_list | wc -l)

if [ -z $3 ]; then
    LOG_OPTIONS="-o pssh-log/stdout -e pssh-log/stderr"
else
    LOG_OPTIONS="-i"
fi

parallel-ssh ${LOG_OPTIONS} -t 0 -p ${NUM_roles} -h ${role}_list -x "-oStrictHostKeyChecking=no -oUserKnownHostsFile=/dev/null -i ../ClusterBootstrap/deploy/sshkey/id_rsa" -l core "${cmd}"