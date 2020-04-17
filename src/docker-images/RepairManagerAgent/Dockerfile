FROM ubuntu:18.04
MAINTAINER Deborah Sandoval <Deborah.Sandoval@microsoft.com>

RUN apt-get update && apt-get --no-install-recommends install -y \
    python3.5 \
    python3-pip \
    systemd-sysv

RUN pip3 install wheel
RUN pip3 install setuptools
RUN pip3 install requests
RUN pip3 install pyyaml

COPY run.sh /
RUN chmod +x /run.sh

ADD RepairManagerAgent /DLWorkspace/src/RepairManagerAgent

CMD /run.sh
