#!/bin/bash

role=$1
file=$2
remote=$3

CLUSTER_NAME=$(grep cluster_name ../ClusterBootstrap/cluster.yaml | awk '{print $2}' | tr '[:upper:]' '[:lower:]')

if [ ! -e ${role}_list ];then

	grep -B3 "role: ${role}" ../ClusterBootstrap/cluster.yaml | grep ${CLUSTER_NAME}- | sed 's/://g' | awk '{print $1}' | grep -v "#" | awk '{printf("%s.%s\n", $1, DOMAIN_SUFFIX)}' DOMAIN_SUFFIX=$(grep domain ../ClusterBootstrap/cluster.yaml | awk '{print $2}') | sort > ${role}_list

fi;

NUM_role=$(cat ${role}_list  | wc -l)


parallel-scp -t 0 -p ${NUM_role} -h ${role}_list  -x "-oStrictHostKeyChecking=no -oUserKnownHostsFile=/dev/null -i ../ClusterBootstrap/deploy/sshkey/id_rsa" -l core $file $remote