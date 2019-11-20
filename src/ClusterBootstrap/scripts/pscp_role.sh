#!/bin/bash

role=$1
file=$2
remote=$3

SCRIPT=`realpath $0`
SCRIPTPATH=`dirname $SCRIPT`

mkdir -p $SCRIPTPATH/../ContinuousIntegration

CLUSTER_NAME=$(grep cluster_name $SCRIPTPATH/../cluster.yaml | awk '{print $2}' | tr '[:upper:]' '[:lower:]')

if [ ! -e $SCRIPTPATH/../ContinuousIntegration/${role}_list ];then

	grep -B3 "role: ${role}" $SCRIPTPATH/../cluster.yaml | grep ${CLUSTER_NAME}- | sed 's/://g' | awk '{print $1}' | grep -v "#" | awk '{printf("%s.%s\n", $1, DOMAIN_SUFFIX)}' DOMAIN_SUFFIX=$(grep domain $SCRIPTPATH/../cluster.yaml | awk '{print $2}') | sort > $SCRIPTPATH/../ContinuousIntegration/${role}_list

fi;

NUM_role=$(cat $SCRIPTPATH/../ContinuousIntegration/${role}_list  | wc -l)


parallel-scp -t 0 -p ${NUM_role} -h $SCRIPTPATH/../ContinuousIntegration/${role}_list  -x "-oStrictHostKeyChecking=no -oUserKnownHostsFile=/dev/null -i $SCRIPTPATH/../deploy/sshkey/id_rsa" -l core $file $remote