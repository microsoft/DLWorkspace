#!/bin/bash
# Install python on CoreOS base image
SHORTVER="2.7.13"
VERSIONS="2.7.13.2715"
PYTHONFILE="ActivePython-2.7.13.2715-linux-x86_64-glibc-2.12-402695.tar.gz"
UNTARFILE="ActivePython-2.7.13.2715-linux-x86_64-glibc-2.12-402695"

# make directory

if [ -e /opt/bin/python ]; 
then 
CURVER=$(/opt/bin/python --version 2>&1)
else
CURVER=""
fi

echo "${CURVER}"
#echo "Python ${SHORTVER}"
if [ "${CURVER}" != "Python ${SHORTVER}" ]
then
pushd .
rm -rf /tmp/install-python
mkdir /tmp/install-python
cd /tmp/install-python
rm ${PYTHONFILE}
while [ ! -e ${PYTHONFILE} ]; do
	wget http://downloads.activestate.com/ActivePython/releases/${VERSIONS}/${PYTHONFILE}
done
tar -xzvf ${PYTHONFILE}

sudo mkdir /opt/python${SHORTVER}
mv ${UNTARFILE} apy && cd apy && sudo ./install.sh -I /opt/python${SHORTVER}

sudo rm /opt/bin/easy_install
sudo rm /opt/bin/pip
sudo rm /opt/bin/python
sudo rm /opt/bin/virtualenv
# Put all links in /opt/bin, which is in default $PATH of CoreOS
sudo mkdir /opt/bin
sudo ln -s /opt/python${SHORTVER}/bin/easy_install /opt/bin/easy_install
sudo ln -s /opt/python${SHORTVER}/bin/pip /opt/bin/pip
sudo ln -s /opt/python${SHORTVER}/bin/python /opt/bin/python
sudo ln -s /opt/python${SHORTVER}/bin/virtualenv /opt/bin/virtualenv
	
popd
rm -rf /tmp/install-python

fi