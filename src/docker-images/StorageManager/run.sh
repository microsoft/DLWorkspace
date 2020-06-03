#!/bin/bash

_broadcast() {
    kill -SIGTERM -"$cur_pgid"
}

cur_pgid=`ps -o '%r' $$ | tail -n 1 | sed "s/ //g"`

trap _broadcast SIGTERM

rm -f /DLWorkspace/src/StorageManager/config.yaml
ln -s /StorageManager/config.yaml /DLWorkspace/src/StorageManager/config.yaml

python3 /DLWorkspace/src/StorageManager/main.py &
wait # for SIGTERM to deliver
