#!/bin/bash

role=$1

SCRIPT=`realpath $0`
SCRIPTPATH=`dirname $SCRIPT`
echo $SCRIPTPATH
cd $SCRIPTPATH/..

mkdir -p ContinuousIntegration
# cd ../ContinuousIntegration
./deploy.py kubectl get nodes | awk '$2=="Ready" {print $1}' | grep $role | sort > ContinuousIntegration/${role}_ready


CLUSTER_NAME=$(grep cluster_name cluster.yaml | awk '{print $2}' | tr '[:upper:]' '[:lower:]')
if [ ! -e ContinuousIntegration/${role}_name_list ];then
	grep -B3 "role: ${role}" cluster.yaml | grep ${CLUSTER_NAME}- | sed 's/://g' | awk '{print $1}' | sort > ContinuousIntegration/${role}_name_list
fi;

nonready=`diff ContinuousIntegration/${role}_ready ContinuousIntegration/${role}_name_list`
echo $nonready
rm ContinuousIntegration/${role}_ready
if [ ! -z "$nonready" ]; then
	echo "There're non-ready ${role} nodes: $nonready"
	exit 1
else
	echo "$role nodes ready"
fi;