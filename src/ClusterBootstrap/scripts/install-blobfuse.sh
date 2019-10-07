#!/bin/bash

sudo rm -f packages-microsoft-prod.deb
wget https://packages.microsoft.com/config/ubuntu/16.04/packages-microsoft-prod.deb
sudo dpkg -i packages-microsoft-prod.deb
sudo apt-get update
sudo apt-get install -y blobfuse fuse jq
sudo rm -f packages-microsoft-prod.deb
sudo mkdir /etc/kubernetes/volumeplugins
sed -e 's#ExecStart=/opt/bin/kubelet \\#ExecStart=/opt/bin/kubelet \\\n  --volume-plugin-dir=/etc/kubernetes/volumeplugins \\#g' /etc/systemd/system/kubelet.service > /tmp/newkubelet.service
sudo mv /tmp/newkubelet.service /etc/systemd/system/kubelet.service
sudo systemctl daemon-reload
sudo systemctl restart kubelet
