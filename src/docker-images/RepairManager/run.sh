#!/bin/bash

_broadcast() {
    kill -SIGTERM -"$cur_pgid"
}

cur_pgid=`ps -o '%r' $$ | tail -n 1 | sed "s/ //g"`

trap _broadcast SIGTERM

cd /DLWorkspace/src/RepairManager/
python3 main.py &
wait # for SIGTERM to deliver
