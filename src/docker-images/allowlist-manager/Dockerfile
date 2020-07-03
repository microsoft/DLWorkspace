FROM python:3.7

RUN pip3 install requests python-dateutil pyyaml pytz
RUN curl -sL https://aka.ms/InstallAzureCLIDeb | bash

WORKDIR /allowlist-manager

ADD main.py /allowlist-manager/
