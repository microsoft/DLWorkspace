#!/bin/bash
set -ex

USER=$1
CONFIG_TYPE=$2
waitmin=$3
pollsec=$4
echo $USER
echo $CONFIG_TYPE

./timed_check.sh $waitmin $pollsec ./pscp_role.sh worker check_machine.sh /home/${USER}
./timed_check.sh $waitmin $pollsec ./pssh_role.sh worker \"bash check_machine.sh $CONFIG_TYPE\"
./timed_check.sh $waitmin $pollsec ./check_node_ready.sh infra
./timed_check.sh $waitmin $pollsec ./pscp_role.sh infra check_docker_ready.sh /home/${USER}
./timed_check.sh $waitmin $pollsec ./pssh_role.sh infra \"bash ./check_docker_ready.sh infra\"
./timed_check.sh $waitmin $pollsec ./check_node_ready.sh worker
./timed_check.sh $waitmin $pollsec ./pscp_role.sh worker check_docker_ready.sh /home/${USER}
./timed_check.sh $waitmin $pollsec ./pssh_role.sh worker \"bash ./check_docker_ready.sh worker\"
./timed_check.sh $waitmin $pollsec ./pssh_role.sh worker \"bash ./check_docker_ready.sh postlbl\"
./timed_check.sh $waitmin $pollsec ./pssh_role.sh infra \"bash check_docker_ready.sh services\"
