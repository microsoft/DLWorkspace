#!/bin/sh

# Adopted from https://github.com/lifengli137/gpu
# gpu_topo gives GPUs their original order to avoid NVLink break

set -uex
umask 0077

g++ -o gpu_topo gpu_topo.cpp
