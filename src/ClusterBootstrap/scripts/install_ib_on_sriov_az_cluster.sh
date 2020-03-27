#!/bin/bash

set -x

export DEBIAN_FRONTEND=noninteractive

# Remove kvp file for ND (network direct) - the older mechanism for InfiniBand before SR-IOV retrofit
sudo rm -rf /var/lib/hyperv/.kvp_pool_0
sudo systemctl restart hv-kvp-daemon.service

sudo apt-get update
sudo apt-get --no-install-recommends install -y build-essential python-setuptools libibverbs-dev bison flex ibverbs-utils net-tools gfortran python3-pip
sudo apt-get --no-install-recommends install -y perftest infiniband-diags
sudo python3 -m pip install --upgrade pip setuptools wheel

# Install OFED MLNX (This will override some IB packages above)
wget -q -O - http://www.mellanox.com/downloads/ofed/MLNX_OFED-5.0-1.0.0.0/MLNX_OFED_LINUX-5.0-1.0.0.0-ubuntu18.04-x86_64.tgz | tar xzf -
cd MLNX_OFED_LINUX-5.0-1.0.0.0-ubuntu18.04-x86_64
sudo ./mlnxofedinstall --force
sudo /etc/init.d/openibd restart

sudo apt-get remove -y walinuxagent
sudo apt-get -qq update
sudo apt-get --no-install-recommends install -y walinuxagent

#wget https://github.com/Azure/WALinuxAgent/archive/v2.2.40.tar.gz

#tar -xvf v2.2.40.tar.gz
#cd WALinuxAgent-2.2.40
#sudo python3 setup.py install --register-service --force

sudo sed -i -e 's/# OS.EnableRDMA=y/OS.EnableRDMA=y/g' /etc/waagent.conf
#sudo sed -i -e 's/# AutoUpdate.Enabled=y/AutoUpdate.Enabled=y/g' /etc/waagent.conf
sudo systemctl restart walinuxagent.service

# Set up IB devices
sudo modprobe ib_ipoib
sudo modprobe rdma_ucm
sudo modprobe ib_umad

a=$(grep "^ib_ipoib" /etc/modules)
if [ -z $a ]; then
    echo 'ib_ipoib' | sudo tee -a /etc/modules
fi

a=$(grep "^rdma_ucm" /etc/modules)
if [ -z $a ]; then
    echo 'rdma_ucm' | sudo tee -a /etc/modules
fi

a=$(grep "^ib_umad" /etc/modules)
if [ -z $a ]; then
    echo 'ib_umad' | sudo tee -a /etc/modules
fi

# Update memory limits
touch /tmp/limits.conf
cat > /tmp/limits.conf << EOF
# /etc/security/limits.conf
#
#Each line describes a limit for a user in the form:
#
#<domain>        <type>  <item>  <value>
#
#Where:
#<domain> can be:
#        - a user name
#        - a group name, with @group syntax
#        - the wildcard *, for default entry
#        - the wildcard %, can be also used with %group syntax,
#                 for maxlogin limit
#        - NOTE: group and wildcard limits are not applied to root.
#          To apply a limit to the root user, <domain> must be
#          the literal username root.
#
#<type> can have the two values:
#        - "soft" for enforcing the soft limits
#        - "hard" for enforcing hard limits
#
#<item> can be one of the following:
#        - core - limits the core file size (KB)
#        - data - max data size (KB)
#        - fsize - maximum filesize (KB)
#        - memlock - max locked-in-memory address space (KB)
#        - nofile - max number of open files
#        - rss - max resident set size (KB)
#        - stack - max stack size (KB)
#        - cpu - max CPU time (MIN)
#        - nproc - max number of processes
#        - as - address space limit (KB)
#        - maxlogins - max number of logins for this user
#        - maxsyslogins - max number of logins on the system
#        - priority - the priority to run user process with
#        - locks - max number of file locks the user can hold
#        - sigpending - max number of pending signals
#        - msgqueue - max memory used by POSIX message queues (bytes)
#        - nice - max nice priority allowed to raise to values: [-20, 19]
#        - rtprio - max realtime priority
#        - chroot - change root to directory (Debian-specific)
#
#<domain>      <type>  <item>         <value>
#

#*               soft    core            0
#root            hard    core            100000
#*               hard    rss             10000
#@student        hard    nproc           20
#@faculty        soft    nproc           20
#@faculty        hard    nproc           50
#ftp             hard    nproc           0
#ftp             -       chroot          /ftp
#@student        -       maxlogins       4

# End of file
* hard memlock unlimited
* soft memlock unlimited
* hard nofile 65535
* soft nofile 65535
EOF

sudo cp /tmp/limits.conf /etc/security/limits.conf
