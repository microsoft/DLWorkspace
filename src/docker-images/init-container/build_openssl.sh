#!/bin/sh

set -uex
umask 0077

export CFLAGS="-I$ROOT/usr/include -L. -fPIC -O2"
export CPPFLAGS="-I$ROOT/usr/include -L. -fPIC"

gzip -dc $DIST_DIR/openssl-*.tar.gz |(cd "$BUILD_DIR" && tar xf -)
(
cd "$BUILD_DIR"/openssl-*
./config --prefix="/usr" no-shared
make -j12
make INSTALL_PREFIX="$ROOT" install
)
