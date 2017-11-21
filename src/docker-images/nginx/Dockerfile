FROM library/nginx:1.13.6
MAINTAINER Jin Li <jinlmsft@hotmail.com>

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        git \
        wget \
        vim \
        python-dev \
        python-numpy \
        python-pip \
        python-yaml \
        locales \
        curl \
        apt-transport-https 

#RUN sh -c 'echo "deb [arch=amd64] https://apt-mo.trafficmanager.net/repos/dotnet-release/ xenial main" > /etc/apt/sources.list.d/dotnetdev.list'
#RUN apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 417A0893
#RUN apt-get install -y apt-transport-https
#RUN apt-get update
#RUN apt-get install -y dotnet-dev-1.0.4

# netcore 2.0
RUN pip install --upgrade pip; 

RUN pip install setuptools; 

RUN pip install flask
RUN pip install flask.restful

RUN apt-get install -y --no-install-recommends ssh
RUN apt-get install -y software-properties-common 
RUN add-apt-repository ppa:certbot/certbot
RUN apt-get update; apt-get install -y certbot
