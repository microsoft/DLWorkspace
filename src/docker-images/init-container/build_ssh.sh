#!/bin/sh

set -uex
umask 0077

export CFLAGS="-I$ROOT/usr/include -L. -fPIC"
export CPPFLAGS="-I$ROOT/usr/include -L. -fPIC"

gzip -dc $DIST_DIR/openssh-*.tar.gz |(cd "$BUILD_DIR" && tar xf -)
(
cd "$BUILD_DIR"/openssh-*
cp -p "$ROOT"/usr/lib/*.a .
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
make DESTDIR="$ROOT" install
)
