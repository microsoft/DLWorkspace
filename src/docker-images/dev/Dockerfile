FROM ubuntu:16.04
MAINTAINER Jin Li <jinlmsft@hotmail.com>

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        git \
        wget \
        protobuf-compiler \
        python-dev \
        python-numpy \
        python-pip 
        

# Install docker
RUN apt-get update; apt-get install -y apt-transport-https ca-certificates 

RUN apt-key adv --keyserver hkp://p80.pool.sks-keyservers.net:80 --recv-keys 58118E89F3A912897C070ADBF76221572C52609D

RUN mkdir /etc/apt/source.list.d

RUN echo "deb https://apt.dockerproject.org/repo ubuntu-trusty main" > /etc/apt/sources.list.d/docker.list

RUN apt-get update

RUN apt-cache policy docker-engine

RUN apt-get update

RUN apt-get install -y --no-install-recommends linux-image-extra-$(uname -r) linux-image-extra-virtual

# RUN apt-get update && apt-get install -y docker-engine

# Install go 1.6 (for kubernetes)

RUN wget https://raw.githubusercontent.com/moovweb/gvm/master/binscripts/gvm-installer

RUN bash gvm-installer

RUN apt-get install -y bison curl

RUN chmod +x /root/.gvm/scripts/gvm

ENV PATH="$PATH:/root/.gvm/bin"

RUN /bin/bash -c "source /root/.gvm/scripts/gvm; gvm install go1.4; gvm use go1.4; export GOROOT_BOOTSTRAP=$GOROOT; gvm install go1.7.4; gvm use go1.7.4"

RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -

RUN curl https://packages.microsoft.com/config/ubuntu/16.04/prod.list > /etc/apt/sources.list.d/mssql.list

# Install python for Azure SQL

RUN apt-get update; apt-get install msodbcsql mssql-tools unixodbc-dev-utf16; pip install pyodbc==3.1.1

WORKDIR /home/code

