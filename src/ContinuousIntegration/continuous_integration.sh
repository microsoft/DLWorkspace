#!/bin/bash

set -ex

./pscp_role.sh worker check_machine.sh /home/core
./pssh_role.sh worker "bash check_machine.sh"

./check_node_ready.sh infra
./pscp_role.sh infra check_docker_ready.sh /home/core
./pssh_role.sh infra "bash ./check_docker_ready.sh infra"

./check_node_ready.sh worker
./pscp_role.sh worker check_docker_ready.sh /home/core
./pssh_role.sh worker "bash ./check_docker_ready.sh worker"

./pssh_role.sh worker "bash ./check_docker_ready.sh postlbl"
./pssh_role.sh infra "bash check_docker_ready.sh services"