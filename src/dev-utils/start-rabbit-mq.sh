#!/bin/bash

if [ $# -ne 3 ] ; then
    echo Usage: $0 mq_user mq_pass data-dir >&2
    exit 1
fi

docker kill rabbitmq
docker rm rabbitmq

docker run -d \
    --hostname rabbit1 \
    --name rabbitmq \
    --net=host \
    -v $3:/var/lib/rabbitmq/mnesia/ \
    -e RABBITMQ_DEFAULT_USER=$1 \
    -e RABBITMQ_DEFAULT_PASS=$2 \
    rabbitmq:3
