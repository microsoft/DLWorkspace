FROM ubuntu:18.04
MAINTAINER Hongzhi Li <Hongzhi.Li@microsoft.com>

# See https://stackoverflow.com/questions/37706635/in-docker-apt-get-install-fails-with-failed-to-fetch-http-archive-ubuntu-com
# It is a good practice to merge apt-get update with the following apt-get install
RUN apt-get update;
RUN apt-get update; apt-get install -y --no-install-recommends apt-transport-https \
        build-essential \
        cmake \
        git \
        wget \
        vim \
        python-dev \
        python-pip \
        python-yaml \
        locales \
        python-pycurl \
        bison \
        curl \
        apt-utils


RUN pip install --upgrade pip;

RUN pip install setuptools;
RUN locale-gen en_US.UTF-8
RUN update-locale LANG=en_US.UTF-8

RUN pip install flask
RUN pip install flask.restful
RUN pip install requests
RUN pip install tzlocal

RUN pip install subprocess32
RUN pip install requests


COPY kubectl /usr/local/bin/kubectl
RUN chmod +x /usr/local/bin/kubectl


COPY run.sh /
RUN chmod +x /run.sh

ADD RepairManager /DLWorkspace/src/RepairManager

CMD /run.sh
