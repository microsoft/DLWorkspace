#!/bin/bash
set -ex

USER=$1
CONFIG_TYPE=$2
waitmin=$3
pollsec=$4
echo $USER
echo $CONFIG_TYPE
# check docker and nvidia driver on worker
# cd ..
./scripts/timed_check.sh $waitmin $pollsec "./ctl.py -v -r worker copy2 ./scripts/check_machine.sh /home/${USER}"
./scripts/timed_check.sh $waitmin $pollsec "./ctl.py -v -r worker runcmd \"bash check_machine.sh $CONFIG_TYPE\""
./scripts/timed_check.sh $waitmin $pollsec "./ctl.py -v -r infra copy2 ./scripts/check_docker_ready.sh /home/${USER}"
./scripts//timed_check.sh $waitmin $pollsec "./ctl.py -v -r infra runcmd \"bash check_docker_ready.sh $CONFIG_TYPE\""
./scripts/timed_check.sh $waitmin $pollsec "./ctl.py -v -r worker copy2 ./scripts/check_docker_ready.sh /home/${USER}"
./scripts/timed_check.sh $waitmin $pollsec "./ctl.py -v -r worker runcmd \"bash check_docker_ready.sh $CONFIG_TYPE\""
./scripts/timed_check.sh $waitmin $pollsec "./ctl.py -v -r worker runcmd \"bash check_docker_ready.sh postlbl\""
./scripts/timed_check.sh $waitmin $pollsec "./ctl.py -v -r infra runcmd \"bash check_docker_ready.sh services\""
# verify all nodes ready
./scripts/timed_check.sh $waitmin $pollsec "./ctl.py verifyallnodes"
