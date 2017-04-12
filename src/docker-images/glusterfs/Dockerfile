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


RUN yum -y install epel-release
RUN yum -y update; 
RUN yum -y install python-pip python-argparse

RUN rm /usr/bin/python
RUN ln -s /usr/src/Python-2.7.13/python /usr/bin/python

RUN pip install --upgrade pip; 
RUN pip install setuptools 
RUN pip install pyyaml jinja2 argparse

ENV PYTHONPATH $PYTHONPATH:/usr/lib64/python2.7/site-packages/
# Move 
WORKDIR /opt/glusterfs
ADD launch_glusterfs.py /opt/glusterfs/
ADD glusterfs_config.yaml /opt/glusterfs/
ADD logging.yaml /opt/glusterfs/
RUN chmod +x /opt/glusterfs/launch_glusterfs.py
CMD /opt/glusterfs/launch_glusterfs.py run ; exec /bin/bash -c "trap : TERM INT; sleep infinity & wait"






