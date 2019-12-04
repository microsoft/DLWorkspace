FROM ubuntu:16.04 as builder

RUN apt-get update && apt-get install -y wget gzip build-essential

WORKDIR /ssh_build

COPY build-openssh-static.sh /ssh_build
RUN sh build-openssh-static.sh

FROM python:3.8.0-alpine3.10

WORKDIR /dlts-init
COPY requirements.txt /dlts-init

RUN pip3 install -r /dlts-init/requirements.txt

COPY --from=builder /ssh_build/root /dlts-init/ssh_build

COPY install.sh init.sh /dlts-init/
COPY ssh_config /dlts-init/ssh_config
COPY runtime /dlts-init/runtime
