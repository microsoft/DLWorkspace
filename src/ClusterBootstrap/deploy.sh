#!/bin/bash
rm -rf deploy/* cloudinit* az_complementary.yaml
# # render
./cloud_init_deploy.py clusterID
./cloud_init_aztools.py -cnf config.yaml -o az_complementary.yaml prerender
# # render templates and prepare binaries
./cloud_init_deploy.py -cnf config.yaml -cnf az_complementary.yaml render
# # pack, push dockers, generate az cli commands to add machines
./cloud_init_deploy.py -cnf config.yaml -cnf az_complementary.yaml pack
# # push dockers
./cloud_init_deploy.py -cnf config.yaml -cnf az_complementary.yaml docker servicesprerequisite
# # # generate
./cloud_init_aztools.py -cnf config.yaml -cnf az_complementary.yaml deploy
# # deploy
./scripts/deploy_framework.sh
./scripts/add_machines.sh
./cloud_init_aztools.py -cnf config.yaml -cnf az_complementary.yaml interconnect
# # get status
./cloud_init_aztools.py -cnf config.yaml -o brief.yaml listcluster
