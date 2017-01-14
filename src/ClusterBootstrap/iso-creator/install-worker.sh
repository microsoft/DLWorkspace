#!/bin/bash

## If you have provided another name for the cloud-init script, change it here.
## The mountpoint for the VFAT is always /media/usbconfig/
CONFIG="cloud-config-kubelet.yml"
VERSION="current"
CHANNEL="stable"

# Apply the cloud-config yml?
#sudo coreos-cloudinit --from-file=/media/usbconfig/$CONFIG

/bin/bash -c 'until ping -c1 8.8.8.8; do sleep 1; done;'


# Waiting 30 seconds to complete the boot
#sleep 30

DEVICE="/dev/sda"
[ -f /dev/vda ] && DEVICE="/dev/vda"

## UNCOMMENT the following lines to install
logger --tag "coreos-install" --id=$$ --journald -- "Starting install process on $DEVICE"
sudo coreos-install -d $DEVICE -V $VERSION -C $CHANNEL -c /media/usbconfig/$CONFIG
logger --tag "coreos-install" --id=$$ --journald -- "Finished install process on $DEVICE"

#sync
sudo shutdown -h now
