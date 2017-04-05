FROM gluster/gluster-centos:latest
MAINTAINER Jin Li <jinlmsft@hotmail.com>

# Setup python

RUN yum -y update; yum -y groupinstall "Development Tools"

WORKDIR /usr/src
RUN wget https://www.python.org/ftp/python/2.7.13/Python-2.7.13.tgz
RUN tar xzf Python-2.7.13.tgz
WORKDIR /usr/src/Python-2.7.13
RUN ./configure
RUN make altinstall

# RUN dnf install python-systemd python3-systemd

# Move 
WORKDIR /opt/glusterfs
ADD launch_glusterfs.py /opt/glusterfs/
RUN chmod +x /opt/glusterfs/launch_glusterfs.py
CMD /opt/glusterfs/launch_glusterfs.py






