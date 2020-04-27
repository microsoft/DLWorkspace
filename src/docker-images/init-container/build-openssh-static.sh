#!/bin/sh

set -uex
umask 0077

export DIST_DIR=dist
top="$(pwd)"
export ROOT="$top/root"
export BUILD="$top/build"

export CFLAGS="-I$ROOT/usr/include -L. -fPIC -O2"
export CPPFLAGS="-I$ROOT/usr/include -L. -fPIC"

rm -rf "$ROOT" "$BUILD"
mkdir -p "$ROOT" "$BUILD"

sh download.sh
sh build_zlib.sh
sh build_openssl.sh
sh build_ssh.sh
