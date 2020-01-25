#!/bin/bash
set -ex

USER=$1
CONFIG_TYPE=$2
waitmin=$3
pollsec=$4
echo $USER
echo $CONFIG_TYPE

./timed_check.sh $waitmin $pollsec "cd ..; ./cluster_ctl.py -v -r worker copy2 ./scripts/check_machine.sh /home/${USER}"
./timed_check.sh $waitmin $pollsec "cd ..; ./cluster_ctl.py -v -r worker runcmd \"bash check_machine.sh $CONFIG_TYPE\""
# check all node ready
./timed_check.sh $waitmin $pollsec "cd ..; ./cluster_ctl.py -v -r infra copy2 ./scripts/check_docker_ready.sh /home/${USER}"
./timed_check.sh $waitmin $pollsec "cd ..; ./cluster_ctl.py -v -r infra runcmd \"bash check_docker_ready.sh $CONFIG_TYPE\""
./timed_check.sh $waitmin $pollsec "cd ..; ./cluster_ctl.py -v -r worker copy2 ./scripts/check_docker_ready.sh /home/${USER}"
./timed_check.sh $waitmin $pollsec "cd ..; ./cluster_ctl.py -v -r worker runcmd \"bash check_docker_ready.sh $CONFIG_TYPE\""
./timed_check.sh $waitmin $pollsec "cd ..; ./cluster_ctl.py -v -r worker runcmd \"bash check_docker_ready.sh postlbl\""
./timed_check.sh $waitmin $pollsec "cd ..; ./cluster_ctl.py -v -r infra runcmd \"bash check_docker_ready.sh services\""
