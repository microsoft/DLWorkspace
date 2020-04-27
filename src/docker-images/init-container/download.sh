#!/bin/sh

set -uex
umask 0077

LIBC_URL="http://ftp.gnu.org/gnu/glibc/glibc-2.31.tar.gz"
ZLIB_URL="https://www.zlib.net/zlib-1.2.11.tar.gz"
SSH_URL="https://cdn.openbsd.org/pub/OpenBSD/OpenSSH/portable/openssh-8.1p1.tar.gz"
SSL_URL="https://www.openssl.org/source/openssl-1.0.2t.tar.gz"

mkdir $DIST_DIR

(cd $DIST_DIR
    wget $LIBC_URL
    wget $ZLIB_URL
    wget $SSH_URL
    wget $SSL_URL
)

rm -rf "$ROOT" "$BUILD_DIR"
mkdir -p "$ROOT" "$BUILD_DIR"
