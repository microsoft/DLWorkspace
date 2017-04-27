#!/bin/bash
# Install python on CoreOS base image
# Docker environment for development of DL workspace
sudo apt-get update 

sudo apt-get install -y --no-install-recommends \
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
        sudo 
        

sudo apt-get install -y bison curl golang-go

# Install docker
curl -q https://get.docker.com/ | sudo bash

sudo usermod -aG docker core

# Install python for Azure SQL

sudo curl https://packages.microsoft.com/keys/microsoft.asc | sudo apt-key add -

sudo curl https://packages.microsoft.com/config/ubuntu/16.04/prod.list | sudo tee /etc/apt/sources.list.d/mssql-release.list

sudo apt-get update; 

sudo ACCEPT_EULA=Y apt-get install -y msodbcsql=13.1.1.0-1

sudo apt-get install -y unixodbc-dev-utf16

#RUN ln -sfn /opt/mssql-tools/bin/sqlcmd-13.0.1.0 /usr/bin/sqlcmd 
#RUN ln -sfn /opt/mssql-tools/bin/bcp-13.0.1.0 /usr/bin/bcp

# RUN apt-get install -y unixodbc unixodbc-dev
# RUN apt-get install -y python-scipy

sudo pip install --upgrade pip; 

sudo pip install setuptools 

sudo pip install pyyaml jinja2
sudo pip install pyodbc flask flask.restful

# en_US.UTF-8 needed to connnect to SQL Azure
sudo locale-gen en_US.UTF-8

sudo update-locale LANG=en_US.UTF-8

# Go editing tools
sudo mkdir /opt/go
sudo export GOPATH=/opt/go

# go get -u github.com/nsf/gocode

# go get golang.org/x/tools/cmd/guru
# go build golang.org/x/tools/cmd/guru
# mv guru $(go env GOROOT)/bin

# go get github.com/rogpeppe/godef
# go build github.com/rogpeppe/godef
# mv godef $(go env GOROOT)/bin

# go get github.com/tools/godep

# chmod -R 0777 /opt/go

