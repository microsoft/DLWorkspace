#!/bin/bash 

sudo apt-get update 
sudo apt-get install -y --no-install-recommends \
        apt-utils \
        software-properties-common \
        git \
        curl \
        python-pip \
        wget \
        cpio \
        mkisofs \
        apt-transport-https \
        openssh-client \
        ca-certificates \
        sshpass

# Install docker
which docker
if [ $? -eq 0 ]
then 
docker --version
## docker already installed
else
curl -q https://get.docker.com/ | sudo bash
fi

sudo usermod -aG docker dlwsadmin

sudo apt-get install -y --no-install-recommends python-yaml python-jinja2 python-setuptools python-tzlocal python-pycurl

git clone http://github.com/Microsoft/DLWorkspace /home/dlwsadmin/dlworkspace
cd /home/dlwsadmin/dlworkspace
git fetch --all
git checkout ARMTemplate

cd /home/dlwsadmin/dlworkspace/src/ClusterBootstrap
../ARM/createconfig.py genconfig --outfile /home/dlwsadmin/dlworkspace/src/ClusterBootstrap/config.yaml $@
./az_tools.py --noaz genconfig

# Generate SSH keys
./deploy.py -y build

# Copy ssh keys
../ARM/createconfig.py sshkey $@

# change owner to dlwsadmin
chown -R dlwsadmin /home/dlwsadmin/dlworkspace

# run deploy script in docker group, using user dlwsadmin
sudo -H -u dlwsadmin sg docker -c "bash /home/dlwsadmin/dlworkspace/src/ARM/deploycluster.sh"

