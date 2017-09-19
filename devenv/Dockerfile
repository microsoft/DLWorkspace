# Docker environment for development of DL workspace
FROM ubuntu:16.04
MAINTAINER Jin Li <jinlmsft@hotmail.com>

# Software package installation
RUN apt-get update && apt-get install -y --no-install-recommends \
        apt-utils \
        software-properties-common \
        build-essential \
        cmake \
        git \
        curl \
        wget \
        protobuf-compiler \
        python-dev \
        python-numpy \
        python-pip \
        cpio \
        mkisofs \
        apt-transport-https \
        openssh-client \
        ca-certificates \
        vim \
        sudo \
        git-all \
        sshpass \
        bison \
        libcurl4-openssl-dev libssl-dev 

RUN curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -

RUN add-apt-repository \
   "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
   $(lsb_release -cs) \
   stable"

RUN apt-key fingerprint 0EBFCD88

# Install docker
RUN apt-get update && apt-get install -y --no-install-recommends docker-ce

# PIP installation
RUN pip install --upgrade pip && pip install setuptools && pip install pyyaml jinja2 flask flask.restful tzlocal pycurl

RUN echo "deb [arch=amd64] https://packages.microsoft.com/repos/azure-cli/ wheezy main" > /etc/apt/sources.list.d/azure-cli.list

RUN apt-key adv --keyserver packages.microsoft.com --recv-keys 417A0893
RUN apt-get update && apt-get install azure-cli




