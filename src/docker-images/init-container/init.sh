#!/bin/sh

set -x

DLTS_RUNTIME_DIR=/dlts-runtime

cp -r /dlts-init/ssh_build $DLTS_RUNTIME_DIR
cp -r /dlts-init/ssh_config $DLTS_RUNTIME_DIR
cp /dlts-init/gpu_topo $DLTS_RUNTIME_DIR
cp -r /dlts-init/install.sh $DLTS_RUNTIME_DIR
cp -r /dlts-init/runtime $DLTS_RUNTIME_DIR
cp /dlts-init/init $DLTS_RUNTIME_DIR
python3 /dlts-init/runtime/sync.py
