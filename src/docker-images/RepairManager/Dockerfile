FROM python:3.7
MAINTAINER Deborah Sandoval <Deborah.Sandoval@microsoft.com>

RUN pip3 install --upgrade pip wheel setuptools requests

COPY kubectl /usr/local/bin/kubectl
RUN chmod +x /usr/local/bin/kubectl

COPY run.sh /
RUN chmod +x /run.sh

ADD RepairManager /DLWorkspace/src/RepairManager

RUN pip3 install -r /DLWorkspace/src/RepairManager/requirements.txt

CMD /run.sh
