# Docker environment for development of DL workspace
FROM ubuntu:16.04
MAINTAINER Jin Li <jinlmsft@hotmail.com>

RUN apt-get update && apt-get install -y --no-install-recommends \
        apt-utils \
        software-properties-common \
        build-essential \
        cmake \
        git-all \
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
        sshpass \
        bison

# Install docker

RUN curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -

RUN add-apt-repository \
   "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
   $(lsb_release -cs) \
   stable"

RUN apt-get update && apt-get install docker-ce

RUN pip install --upgrade pip; 

RUN pip install setuptools 

RUN pip install pyyaml jinja2
RUN pip install pyodbc flask flask.restful

# Go lang

RUN apt-get install -y  curl golang-go

# Install python for Azure SQL

RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -

RUN curl https://packages.microsoft.com/config/ubuntu/16.04/prod.list > /etc/apt/sources.list.d/mssql-release.list

RUN apt-get update; ACCEPT_EULA=Y apt-get install -y msodbcsql=13.1.1.0-1 unixodbc-dev-utf16

#RUN ln -sfn /opt/mssql-tools/bin/sqlcmd-13.0.1.0 /usr/bin/sqlcmd 
#RUN ln -sfn /opt/mssql-tools/bin/bcp-13.0.1.0 /usr/bin/bcp

# RUN apt-get install -y unixodbc unixodbc-dev
# RUN apt-get install -y python-scipy



# en_US.UTF-8 needed to connnect to SQL Azure
RUN locale-gen en_US.UTF-8

RUN update-locale LANG=en_US.UTF-8

# Go editing tools
RUN mkdir /opt/go
ENV GOPATH=/opt/go
ENV PATH=${PATH}:/opt/go/bin

RUN go get -u github.com/nsf/gocode

RUN go get golang.org/x/tools/cmd/guru
RUN go build golang.org/x/tools/cmd/guru
RUN mv guru $(go env GOROOT)/bin

RUN go get github.com/rogpeppe/godef
RUN go build github.com/rogpeppe/godef
RUN mv godef $(go env GOROOT)/bin

RUN go get github.com/tools/godep

RUN chmod -R 0777 /opt/go

RUN apt-get update -y; apt-get install -y sshpass

RUN echo "deb [arch=amd64] https://packages.microsoft.com/repos/azure-cli/ wheezy main" | \
     sudo tee /etc/apt/sources.list.d/azure-cli.list

RUN apt-key adv --keyserver packages.microsoft.com --recv-keys 417A0893
RUN apt apt-get update; apt-get install -y apt-transport-https azure-cli

