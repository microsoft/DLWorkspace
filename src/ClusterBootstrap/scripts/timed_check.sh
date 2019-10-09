#!/bin/bash
total_minute=$1
wait_sec=$2
shift 2
cmd="$*"
start=`date +%s`

while [ true ]; do
	eval $cmd
	status=$?
	if (( $status != 0 )); then
		end=`date +%s`
		runtime=$((end-start))
		if (( $runtime < $total_minute*60 )); then
			sleep ${wait_sec}s
		else
			exit 1
		fi
	else
		exit 0
	fi
done
# ./pscp_role.sh worker check_machine.sh /home/core
# ./pssh_role.sh worker "bash check_machine.sh"

# ./check_node_ready.sh infra
# ./pscp_role.sh infra check_docker_ready.sh /home/core
# ./pssh_role.sh infra "bash ./check_docker_ready.sh infra"

# ./check_node_ready.sh worker
# ./pscp_role.sh worker check_docker_ready.sh /home/core
# ./pssh_role.sh worker "bash ./check_docker_ready.sh worker"

# ./pssh_role.sh worker "bash ./check_docker_ready.sh postlbl"
# ./pssh_role.sh infra "bash check_docker_ready.sh services"