#!/bin/bash
rm -f /DLWorkspace/src/StorageManager/config.yaml
ln -s /StorageManager/config.yaml /DLWorkspace/src/StorageManager/config.yaml

python3 /DLWorkspace/src/StorageManager/main.py
