FROM python:3.7
MAINTAINER Deborah Sandoval <Deborah.Sandoval@microsoft.com>

RUN apt-get update && apt-get --no-install-recommends install -y \
    systemd-sysv

RUN pip3 install wheel setuptools requests pyyaml

COPY run.sh /
RUN chmod +x /run.sh

ADD RepairManagerAgent /DLWorkspace/src/RepairManagerAgent

CMD /run.sh
