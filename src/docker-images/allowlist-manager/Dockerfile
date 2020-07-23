FROM golang:1.12.6-alpine as go-builder
COPY runtime /runtime
RUN go build -o /runtime/init /runtime/init.go


FROM python:3.7

RUN pip3 install requests python-dateutil pyyaml pytz
RUN curl -sL https://aka.ms/InstallAzureCLIDeb | bash

COPY --from=go-builder /runtime/init /usr/local/bin/init

WORKDIR /allowlist-manager

ADD main.py /allowlist-manager/
