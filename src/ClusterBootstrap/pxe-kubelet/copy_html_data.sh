#!/bin/bash


cd ~
git clone https://dlws-deploy:msft2016@github.com/MSRCCS/DLWorkspace.git DLWorkspace
cp -R ~/DLWorkspace/src/ClusterBootstrap/pxe-kubelet/www/* /var/www/html
cp -R ~/DLWorkspace/src/ClusterBootstrap/pxe-kubelet/tftp/* /var/lib/tftpboot/


cd /var/www/html
mkdir coreos
cd coreos
mkdir 1185.3.0
cd 1185.3.0
wget -q http://ccsdatarepo.westus.cloudapp.azure.com/data/coreos/coreos/1185.3.0/coreos_production_image.bin.bz2
wget -q http://ccsdatarepo.westus.cloudapp.azure.com/data/coreos/coreos/1185.3.0/coreos_production_image.bin.bz2.sig

cd /var/lib/tftpboot/
wget -q https://stable.release.core-os.net/amd64-usr/current/coreos_production_pxe.vmlinuz 
wget -q https://stable.release.core-os.net/amd64-usr/current/coreos_production_pxe.vmlinuz.sig 
wget -q https://stable.release.core-os.net/amd64-usr/current/coreos_production_pxe_image.cpio.gz 
wget -q https://stable.release.core-os.net/amd64-usr/current/coreos_production_pxe_image.cpio.gz.sig
chmod -R 777 /var/lib/tftpboot/

