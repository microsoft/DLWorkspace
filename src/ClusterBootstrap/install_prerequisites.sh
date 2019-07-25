#!/bin/bash 
sudo apt-get update 
sudo apt-get install -y --no-install-recommends \
        apt-utils \
        software-properties-common \
        git \
        curl \
        python-dev \
        python-pip \
        wget \
        cpio \
        mkisofs \
        apt-transport-https \
        openssh-client \
        ca-certificates 

sudo apt-get install libcurl4-openssl-dev libssl-dev gcc libnss3-dev libgnutls28-dev
sudo apt-get install -y python-subprocess32
# Install docker
# curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -

# sudo add-apt-repository  "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" docker-ce
sudo apt install docker.io

AZ_REPO=$(lsb_release -cs)
echo "deb [arch=amd64] https://packages.microsoft.com/repos/azure-cli/ $AZ_REPO main" | \
    sudo tee /etc/apt/sources.list.d/azure-cli.list

sudo apt-key --keyring /etc/apt/trusted.gpg.d/Microsoft.gpg adv \
     --keyserver packages.microsoft.com \
     --recv-keys BC528686B50D79E339D3721CEB3E94ADBE1229CF

sudo apt-get update
sudo apt-get install -y --no-install-recommends
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash 

# pip install --upgrade pip
sudo pip install setuptools && pip install pyyaml && pip install jinja2 && pip install requests && pip install tzlocal && pip install pycurl

sudo echo "dockerd > /dev/null 2>&1 &" | cat >> /etc/bash.bashrc


# SUBSCRIPTION_NAME="AI Platform GPU - Bing Training" 
# for BING developers, remember to set correct subscription_name
SUBSCRIPTION_NAME="Bing DLTS" 
az login
az account set --subscription "${SUBSCRIPTION_NAME}" 
az account list | grep -A5 -B5 '"isDefault": true'