FROM ubuntu:18.04
MAINTAINER Deborah Sandoval <Deborah.Sandoval@microsoft.com>

RUN apt-get update && apt-get --no-install-recommends install -y \
    python3.7 \
    python3-pip

RUN pip3 install wheel setuptools requests kubernetes flask flask-cors prometheus_client

ADD RepairManager/src/* /repairmanager/

