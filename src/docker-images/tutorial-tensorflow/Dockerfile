#FROM ubuntu:16.04
FROM tensorflow/tensorflow:1.8.0-devel-gpu-py3
MAINTAINER Katherine Li <kml11@live.com>

RUN umask 022
RUN apt-get -y update && \
    apt-get -y install \
      vim \
      wget \
      curl \
      jq \
      gawk \
      openssh-client \
      git \
      rsync \
      sudo 

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


RUN apt-get update -y && \
    apt-get -y install apache2 libapache2-mod-wsgi-py3

RUN git clone https://github.com/tensorflow/models

RUN mkdir -p /var/www/html/

RUN apt-get update -y && apt-get install -y python3-dev python3-pip python3-yaml python3-pycurl locales ssh-askpass
RUN pip3 install --upgrade pip 
RUN pip3 install setuptools 
RUN pip3 install flask flask.restful 
RUN pip3 install bs4 requests 
RUN pip3 install -U flask-cors
RUN pip3 install opencv-python pandas
RUN pip3 install keras 
RUN pip3 install -U --no-cache-dir git+https://github.com/ppwwyyxx/tensorpack.git


RUN apt-get update -y && apt-get install -y nodejs python3-pydot python3-skimage python3-tk screen
RUN pip3 install git+https://github.com/aleju/imgaug

# RUN sudo npm install bower -g 

# netcore 2.0
RUN curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > microsoft.gpg
RUN mv microsoft.gpg /etc/apt/trusted.gpg.d/microsoft.gpg
RUN sh -c 'echo "deb [arch=amd64] https://packages.microsoft.com/repos/microsoft-ubuntu-xenial-prod xenial main" > /etc/apt/sources.list.d/dotnetdev.list'
RUN apt-get update
RUN apt-get install -y dotnet-sdk-2.0.0
RUN apt-get install -y aspnetcore-store-2.0.0

ENV APACHE_RUN_USER www-data
ENV APACHE_RUN_GROUP www-data
ENV APACHE_LOG_DIR /var/log/apache2

#EXPOSE 80
#EXPOSE 5000



RUN rm /etc/apache2/mods-enabled/mpm_*
COPY mpm_prefork.conf /etc/apache2/mods-available/mpm_prefork.conf
COPY 000-default.conf /etc/apache2/sites-available/000-default.conf
COPY ports.conf /etc/apache2/ports.conf
RUN ln -s /etc/apache2/mods-available/mpm_prefork.conf /etc/apache2/mods-enabled/mpm_prefork.conf
RUN ln -s /etc/apache2/mods-available/mpm_prefork.load /etc/apache2/mods-enabled/mpm_prefork.load
COPY bingserver-restfulapi.wsgi /wsgi/bingserver-restfulapi.wsgi
ADD RestAPI /BingServer/src/RestAPI

#ADD utils /BingServer/src/RestAPI/utils
RUN echo "ServerName localhost" >> /etc/apache2/apache2.conf
ADD run.sh /run.sh
RUN chmod +x /run.sh

RUN apt-get update -y && apt-get install -y openssh-server sudo
RUN pip3 install --upgrade --ignore-installed setuptools 

RUN git clone https://github.com/ppwwyyxx/tensorpack.git

RUN mkdir -p /var/log/apache2
RUN chmod 0777 /var/log/apache2
RUN chmod -R 0777 /root
RUN chmod -R 0777 /tensorflow

# RUN apt-get update -y && apt-get install ssh-askpass rssh molly-guard ufw monkeysphere python3-ndg-httpsclient -y
RUN curl -L "https://storage.googleapis.com/download.tensorflow.org/models/inception_v3_2016_08_28_frozen.pb.tar.gz" | tar -C /tensorflow/tensorflow/examples/label_image/data -xz

ENV LD_LIBRARY_PATH /usr/local/nvidia/lib64/

EXPOSE 180 1443 1280
ADD RecogServer /RecogServer
COPY wwwroot /var/www/html
RUN chmod -R 755 /var/www/html/

#Telemetry
#--------------
#The .NET Core tools collect usage data in order to improve your experience. The data is anonymous and does not include command-line arguments. The data is collected by Microsoft and shared with the community.
#You can opt out of telemetry by setting a DOTNET_CLI_TELEMETRY_OPTOUT environment variable to 1 using your favorite shell.
#You can read more about .NET Core tools telemetry @ https://aka.ms/dotnet-cli-telemetry.
ENV DOTNET_CLI_TELEMETRY_OPTOUT 1
#WORKDIR /var/www/html
#RUN bower --allow-root install ng-file-upload --save

# Need to run privileged mode
# python /root/certificate-service/genkey-restapi.py && 

# Additional utility
RUN mkdir /utils; cd /utils;  git clone --recurse-submodules git://github.com/DLWorkspace/DLWorkspace-Utils

# CMD /bin/bash -c "service apache2 start && sleep infinity"
WORKDIR /tensorflow


CMD /bin/bash -c /run.sh
