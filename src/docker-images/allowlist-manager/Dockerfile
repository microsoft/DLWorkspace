FROM python:3.7

RUN pip3 install requests
RUN curl -sL https://aka.ms/InstallAzureCLIDeb | bash

WORKDIR /allowlist-manager

ADD main.py /allowlist-manager/
