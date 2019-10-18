#!/bin/bash

cp /etc/sysctl.conf /tmp/sysctl.conf

# Force gc to clean-up quickly
grep -xF "net.ipv4.neigh.default.gc_interval = 3600" /tmp/sysctl.conf || echo "net.ipv4.neigh.default.gc_interval = 3600" | sudo tee -a /tmp/sysctl.conf

# Set ARP cache entry timeout
grep -xF "net.ipv4.neigh.default.gc_stale_time = 3600" /tmp/sysctl.conf || echo "net.ipv4.neigh.default.gc_stale_time = 3600" | sudo tee -a  /tmp/sysctl.conf

# Setup DNS threshold for arp
grep -xF "net.ipv4.neigh.default.gc_thresh3 = 8192" /tmp/sysctl.conf || echo "net.ipv4.neigh.default.gc_thresh3 = 4096" | sudo tee -a /tmp/sysctl.conf
grep -xF "net.ipv4.neigh.default.gc_thresh2 = 2048" /tmp/sysctl.conf || echo "net.ipv4.neigh.default.gc_thresh2 = 2048" | sudo tee -a /tmp/sysctl.conf
grep -xF "net.ipv4.neigh.default.gc_thresh1 = 1024" /tmp/sysctl.conf || echo "net.ipv4.neigh.default.gc_thresh1 = 1024" | sudo tee -a /tmp/sysctl.conf

sudo cp /tmp/sysctl.conf /etc/sysctl.conf

sudo sysctl -p