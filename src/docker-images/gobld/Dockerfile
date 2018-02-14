FROM ubuntu:16.04
MAINTAINER Sanjeev Mehrotra <sanjeevm0@hotmail.com>

RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        curl \
        apt-utils \
        ssh \
        mercurial \
        wget

# Developer tools / certificates
RUN apt-get install -y --no-install-recommends build-essential
RUN apt-get install -y --no-install-recommends ca-certificates
RUN apt-get install -y --no-install-recommends software-properties-common
RUN update-ca-certificates

# Install Go
ENV GOVERSION=1.9.2
ENV GOOS=linux
ENV GOARCH=amd64
RUN wget https://storage.googleapis.com/golang/go$GOVERSION.$GOOS-$GOARCH.tar.gz
RUN echo go$GOVERSION.$GOOS-$GOARCH.tar.gz
RUN tar -C /usr/local -xzf go$GOVERSION.$GOOS-$GOARCH.tar.gz
RUN rm go$GOVERSION.$GOOS-$GOARCH.tar.gz
ENV PATH=$PATH:/usr/local/go/bin
RUN mkdir /go
RUN mkdir /go/src
ENV GOPATH=/go

# SSH Keys
# COPY gittoken /root
# RUN chmod 400 /root/gittoken

# Install prerequisites
# Install docker - not really needed for building, but makefile checks for it
RUN apt-get install -y --no-install-recommends apt-transport-https
RUN curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -
RUN add-apt-repository \
   "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
   $(lsb_release -cs) \
   stable"
RUN apt-get update && apt-get install -y --no-install-recommends \
    docker-ce
RUN apt-get install -y --no-install-recommends rsync

RUN go get github.com/tools/godep
RUN go get github.com/golang/glog

RUN mkdir /root/.ssh
RUN ssh-keyscan github.com >> /root/.ssh/known_hosts

# change to allow adding of other go packages directly into desired directory
ENV GOPATH=/home:/go

