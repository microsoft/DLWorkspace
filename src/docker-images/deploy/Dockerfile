FROM ubuntu:16.04
MAINTAINER Sanjeev Mehrotra <sanjeevm0@hotmail.com>

RUN apt-get update && apt-get install -y --no-install-recommends \
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
        ca-certificates 

# Install docker
RUN curl -fsSL https://yum.dockerproject.org/gpg | apt-key add -
RUN add-apt-repository \
       "deb https://apt.dockerproject.org/repo/ \
       ubuntu-$(lsb_release -cs) \
       main"
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    docker-engine

RUN pip install --upgrade pip
RUN pip install setuptools && pip install pyyaml && pip install jinja2

RUN echo "dockerd > /dev/null 2>&1 &" | cat >> /etc/bash.bashrc

