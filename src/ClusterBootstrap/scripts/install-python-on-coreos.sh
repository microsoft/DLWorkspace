#!/bin/bash
SHORTVER="2.7"
VERSIONS="2.7.13.2713"
PYTHONFILE="ActivePython-2.7.13.2713-linux-x86_64-glibc-2.3.6-401785.tar.gz"
UNTARFILE="ActivePython-2.7.13.2713-linux-x86_64-glibc-2.3.6-401785"

# make directory
pushd .
rm -rf /tmp/install-python
mkdir /tmp/install-python
cd /tmp/install-python
wget http://downloads.activestate.com/ActivePython/releases/${VERSIONS}/${PYTHONFILE}
tar -xzvf ${PYTHONFILE}

sudo mkdir /opt/python${SHORTVER}
mv ${UNTARFILE} apy && cd apy && sudo ./install.sh -I /opt/python${SHORTVER}

sudo rm /opt/bin/easy_install
sudo rm /opt/bin/pip
sudo rm /opt/bin/python
sudo rm /opt/bin/virtualenv
# Put all links in /opt/bin, which is in default $PATH of CoreOS
mkdir /opt/bin
sudo ln -s /opt/python${SHORTVER}/bin/easy_install /opt/bin/easy_install
sudo ln -s /opt/python${SHORTVER}/bin/pip /opt/bin/pip
sudo ln -s /opt/python${SHORTVER}/bin/python /opt/bin/python
sudo ln -s /opt/python${SHORTVER}/bin/virtualenv /opt/bin/virtualenv
	
popd
rm -rf /tmp/install-python

