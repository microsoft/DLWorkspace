#!/bin/bash

VERSIONS=${VERSIONS:-"2.7.8.10"}

# make directory
if [[ ! -f /opt/bin/python ]]; then
	pushd .
	mkdir /tmp/install-python
	cd /tmp/install-python
	wget http://downloads.activestate.com/ActivePython/releases/${VERSIONS}/ActivePython-${VERSIONS}-linux-x86_64.tar.gz
	tar -xzvf ActivePython-${VERSIONS}-linux-x86_64.tar.gz

	sudo mkdir /opt/python${VERSIONS}
	mv ActivePython-${VERSIONS}-linux-x86_64 apy && cd apy && sudo ./install.sh -I /opt/python${VERSIONS}

	sudo ln -s /opt/python${VERSIONS}/bin/easy_install /opt/bin/easy_install
	sudo ln -s /opt/python${VERSIONS}/bin/pip /opt/bin/pip
	sudo ln -s /opt/python${VERSIONS}/bin/python /opt/bin/python
	sudo ln -s /opt/python${VERSIONS}/bin/virtualenv /opt/bin/virtualenv
	
	popd
	rm -rf /tmp/install-python
fi 
export PATH=/opt/python${VERSIONS}/bin:$PATH