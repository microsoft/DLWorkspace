#!/bin/bash
ssh-keyscan github.com >> /root/.ssh/known_hosts
rm -r /DLWorkspace
ssh-agent bash -c 'ssh-add /root/.ssh/id_rsa; git clone -b webUI git@github.com:MSRCCS/DLWorkspace.git /DLWorkspace'
cp /RestfulAPI/config.yaml /DLWorkspace/src/utils/config.yaml
/pullsrc.sh &

cd /DLWorkspace/src/utils
python /DLWorkspace/src/utils/JobScheduler.py