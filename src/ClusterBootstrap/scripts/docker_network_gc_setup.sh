#!/bin/bash

cp /etc/sysctl.conf /tmp/sysctl.conf

# Force gc to clean-up quickly
grep -xF "net.ipv4.neigh.default.gc_interval = 3600" /tmp/sysctl.conf || sudo tee -a "net.ipv4.neigh.default.gc_interval = 3600" /tmp/sysctl.conf

# Set ARP cache entry timeout
grep -xF "net.ipv4.neigh.default.gc_stale_time = 3600" /tmp/sysctl.conf || sudo tee -a "net.ipv4.neigh.default.gc_stale_time = 3600" /tmp/sysctl.conf

# Setup DNS threshold for arp
grep -xF "net.ipv4.neigh.default.gc_thresh3 = 4096" /tmp/sysctl.conf || sudo tee -a "net.ipv4.neigh.default.gc_thresh3 = 4096" /tmp/sysctl.conf
grep -xF "net.ipv4.neigh.default.gc_thresh2 = 2048" /tmp/sysctl.conf || sudo tee -a "net.ipv4.neigh.default.gc_thresh2 = 2048" /tmp/sysctl.conf
grep -xF "net.ipv4.neigh.default.gc_thresh1 = 1024" /tmp/sysctl.conf || sudo tee -a "net.ipv4.neigh.default.gc_thresh1 = 1024" /tmp/sysctl.conf

sudo cp /tmp/sysctl.conf /etc/sysctl.conf

sudo sysctl -p
