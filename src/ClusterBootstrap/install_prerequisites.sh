# !/bin/bash 
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
        ca-certificates \
        network-manager

sudo apt-get install libcurl4-openssl-dev libssl-dev gcc libnss3-dev libgnutls28-dev
sudo apt-get install -y python-subprocess32
# Install docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -

sudo add-apt-repository  "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
sudo apt install docker.io
sudo apt install pssh

AZ_REPO=$(lsb_release -cs)
echo "deb [arch=amd64] https://packages.microsoft.com/repos/azure-cli/ $AZ_REPO main" | \
    sudo tee /etc/apt/sources.list.d/azure-cli.list

sudo apt-key --keyring /etc/apt/trusted.gpg.d/Microsoft.gpg adv \
     --keyserver packages.microsoft.com \
     --recv-keys BC528686B50D79E339D3721CEB3E94ADBE1229CF

sudo apt-get update
sudo apt-get install -y --no-install-recommends
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash 

pip install --upgrade pip
pip install setuptools && pip install pyyaml && pip install jinja2 && pip install requests && pip install tzlocal && pip install pycurl

sudo echo "dockerd > /dev/null 2>&1 &" | cat >> /etc/bash.bashrc
sudo usermod -aG docker $USER
sudo shutdown -r