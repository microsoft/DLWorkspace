#!/bin/sh

set -uex
umask 0077

export CFLAGS="-I$ROOT/usr/include -L. -fPIC -O2"
export CPPFLAGS="-I$ROOT/usr/include -L. -fPIC"

gzip -dc dist/zlib-*.tar.gz |(cd "$BUILD_DIR" && tar xf -)
(
cd "$BUILD_DIR"/zlib-*
./configure --prefix="$ROOT/usr" --static
make -j12
make install
)
