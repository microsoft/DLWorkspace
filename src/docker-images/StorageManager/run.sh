#!/bin/bash
rm /DLWorkspace/src/utils/config.yaml
ln -s /StorageManager/config.yaml /DLWorkspace/src/utils/config.yaml

python /DLWorkspace/src/StorageManager/main.py
