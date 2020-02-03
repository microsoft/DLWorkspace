#!/bin/bash
rm -rf deploy/* cloudinit* az_complementary.yaml
# render
./cloud_init_deploy.py clusterID
./cloud_init_aztools.py prerender
# render templates and prepare binaries
./cloud_init_deploy.py render
# pack files for cloudinit into a tar file which would be pushed to cloudinit docker
./cloud_init_deploy.py pack
# push dockers
./cloud_init_deploy.py docker servicesprerequisite
# generate scripts
./cloud_init_aztools.py -v deploy
# deploy
./cloud_init_aztools.py interconnect
# get status
./cloud_init_aztools.py listcluster
