#!/bin/sh

set -u
set -e
set -x
umask 0077

ZLIB_URL="https://www.zlib.net/zlib-1.2.11.tar.gz"
SSH_URL="https://cdn.openbsd.org/pub/OpenBSD/OpenSSH/portable/openssh-8.1p1.tar.gz"
SSL_URL="https://www.openssl.org/source/openssl-1.0.2t.tar.gz"

mkdir dist

(cd dist
    wget $ZLIB_URL
    wget $SSH_URL
    wget $SSL_URL
)

top="$(pwd)"
root="$top/root"
build="$top/build"

export CFLAGS="-I$root/usr/include -L. -fPIC"
export CPPFLAGS="-I$root/usr/include -L. -fPIC"

rm -rf "$root" "$build"
mkdir -p "$root" "$build"

gzip -dc dist/zlib-*.tar.gz |(cd "$build" && tar xf -)
cd "$build"/zlib-*
./configure --prefix="$root/usr" --static
make -j12
make install
cd "$top"

gzip -dc dist/openssl-*.tar.gz |(cd "$build" && tar xf -)
cd "$build"/openssl-*
./config --prefix="/usr" no-shared
make -j12
make INSTALL_PREFIX="$root" install
cd "$top"

gzip -dc dist/openssh-*.tar.gz |(cd "$build" && tar xf -)
cd "$build"/openssh-*
cp -p "$root"/usr/lib/*.a .
[ -f sshd_config.orig ] || cp -p sshd_config sshd_config.orig
sed \
  -e 's/^#\(PubkeyAuthentication\) .*/\1 yes/' \
  -e '/^# *Kerberos/d' \
  -e '/^# *GSSAPI/d' \
  -e 's/^#\([A-Za-z]*Authentication\) .*/\1 no/' \
  sshd_config.orig \
  >sshd_config \
;
./configure --prefix="/usr" --with-privsep-user=nobody --with-privsep-path="/var/run/sshd"
make -j12
make DESTDIR="$root" install
