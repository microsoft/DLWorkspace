sudo sed -i '0,/^#\sdeb-src /{s//deb-src /}' /etc/apt/sources.list
sudo apt-get update
sudo apt-get build-dep -y linux-headers-$(uname -r)
sudo apt-get --no-install-recommends install -y libtool libyaml-dev ed libreadline-dev dpatch libsnmp-dev mpi-default-dev module-assistant libselinux-dev quilt fakeroot
git clone git://git.whamcloud.com/fs/lustre-release.git
cd lustre-release
git checkout b2_13
git reset --hard && git clean -dfx
sh autogen.sh && ./configure --disable-server --with-linux=/usr/src/linux-headers-$(uname -r) && make debs -j $(nproc)
cp $(ls debs/lustre-client-modules*) ..
cp $(ls debs/lustre-client-utils*) ..