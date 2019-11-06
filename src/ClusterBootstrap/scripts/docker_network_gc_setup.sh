#!/bin/bash

cp /etc/sysctl.conf /tmp/sysctl.conf

# Force gc to clean-up quickly
grep -xF "net.ipv4.neigh.default.gc_interval = 1800" /tmp/sysctl.conf || echo "net.ipv4.neigh.default.gc_interval = 1800" | sudo tee -a /tmp/sysctl.conf

# Set ARP cache entry timeout
grep -xF "net.ipv4.neigh.default.gc_stale_time = 1800" /tmp/sysctl.conf || echo "net.ipv4.neigh.default.gc_stale_time = 1800" | sudo tee -a  /tmp/sysctl.conf

# Setup DNS threshold for arp
# Check ARP Cache section of post: https://openai.com/blog/scaling-kubernetes-to-2500-nodes
grep -xF "net.ipv4.neigh.default.gc_thresh1 = 80000" /tmp/sysctl.conf || echo "net.ipv4.neigh.default.gc_thresh1 = 80000" | sudo tee -a /tmp/sysctl.conf
grep -xF "net.ipv4.neigh.default.gc_thresh2 = 90000" /tmp/sysctl.conf || echo "net.ipv4.neigh.default.gc_thresh2 = 90000" | sudo tee -a /tmp/sysctl.conf
grep -xF "net.ipv4.neigh.default.gc_thresh3 = 100000" /tmp/sysctl.conf || echo "net.ipv4.neigh.default.gc_thresh3 = 100000" | sudo tee -a /tmp/sysctl.conf

sudo cp /tmp/sysctl.conf /etc/sysctl.conf

sudo sysctl -p
