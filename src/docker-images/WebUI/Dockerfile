FROM ubuntu:16.04

MAINTAINER Hongzhi Li <Hongzhi.Li@microsoft.com>





RUN apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 3FA7E0328081BFF6A14DA29AA6A19B38D3D831EF

RUN echo "deb http://download.mono-project.com/repo/debian wheezy main" | tee /etc/apt/sources.list.d/mono-xamarin.list

RUN echo "deb http://download.mono-project.com/repo/debian wheezy-apache24-compat main" | tee -a /etc/apt/sources.list.d/mono-xamarin.list

RUN apt-get update --fix-missing

RUN apt-get --no-install-recommends install -y apt-transport-https



RUN sh -c 'echo "deb [arch=amd64] https://apt-mo.trafficmanager.net/repos/dotnet-release/ xenial main" > /etc/apt/sources.list.d/dotnetdev.list'

RUN apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 417A0893

RUN apt-get --no-install-recommends install -y apt-transport-https

RUN apt-get update

RUN apt-get --no-install-recommends install -y dotnet-dev-1.0.0-preview2.1-003177 --allow-unauthenticated

RUN apt-get --no-install-recommends install -y dotnet-dev-1.0.0-preview2-003156 --allow-unauthenticated





RUN apt-get update && apt-get --no-install-recommends install -y \

        build-essential \

        cmake \

        git \

        wget \

        vim \

        python-dev \

        python-numpy \

        python-pip \

        python-yaml \

        locales

        



RUN apt-get --no-install-recommends install -y bison curl nfs-common

RUN pip install --upgrade pip; 



RUN pip install setuptools; 

RUN locale-gen en_US.UTF-8

RUN update-locale LANG=en_US.UTF-8



RUN pip install flask

RUN pip install flask.restful



#this ssh key is used to download DLWorkspace from github. It has read-only access to github repo. 

RUN apt-get --no-install-recommends install -y ssh



WORKDIR /usr/WebPortal



ADD WebPortal /usr/WebPortal

COPY run.sh .

RUN chmod +x run.sh

CMD ./run.sh
