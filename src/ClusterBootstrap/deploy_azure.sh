#!/bin/sh
./deploy.py -y build
./az_tools.py create
./az_tools.py genconfig
./deploy.py --verbose scriptblocks azure
