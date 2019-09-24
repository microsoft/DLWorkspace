#!/bin/bash

set -x

sudo systemctl disable unattended-upgrades

# Remove kernel updates

sed 's/"${distro_id}:${distro_codename}";/\/\/"${distro_id}:${distro_codename}";/g' /etc/apt/apt.conf.d/50unattended-upgrades | sed 's/"${distro_id}:${distro_codename}-security";/\/\/"${distro_id}:${distro_codename}-security";/g' | sed 's/"${distro_id}ESM:${distro_codename}";/\/\/"${distro_id}ESM:${distro_codename}";/g' > /tmp/50unattended-upgrades

sudo cp /tmp/50unattended-upgrades /etc/apt/apt.conf.d/50unattended-upgrades

# Disable periodic unattended-update
sed 's/APT::Periodic::Unattended-Upgrade "1";/APT::Periodic::Unattended-Upgrade "0";/g' /etc/apt/apt.conf.d/20auto-upgrades > /tmp/20auto-upgrades

sudo cp /tmp/20auto-upgrades /etc/apt/apt.conf.d/20auto-upgrades
