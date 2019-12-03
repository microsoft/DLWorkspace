FROM ubuntu:16.04 as builder

RUN apt-get update && apt-get install -y wget gzip build-essential

WORKDIR /ssh_build

COPY build-openssh-static.sh /ssh_build
RUN sh build-openssh-static.sh

#FROM python:3.8.0-alpine3.10
FROM ubuntu:16.04

WORKDIR /ssh_build

COPY --from=builder /ssh_build/root /ssh_build
COPY init.d /ssh_build/init.d
COPY default /ssh_build/default
COPY install.sh /ssh_build
