#!/bin/bash
rm -rf deploy/!\(bin\) cloudinit* !\(config\).yaml
# prepare clusterID
./cloud_init_deploy.py clusterID
# render a machine list which is to be deployed
./cloud_init_aztools.py prerender
# render templates and prepare binaries
./cloud_init_deploy.py render
# pack files for cloudinit into a tar file which would be pushed to cloudinit docker
./cloud_init_deploy.py pack
# push dockers
./cloud_init_deploy.py docker servicesprerequisite
# execute a deployment action based on the rendered files and machine list got in prerender
./cloud_init_aztools.py -v deploy
# get status of the cluster
./cloud_init_aztools.py listcluster
# connect the nodes inside the cluster
./cloud_init_aztools.py interconnect
