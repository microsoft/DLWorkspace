#!/bin/bash

cd /var/www/html
mkdir coreos
cd coreos
mkdir {{cnf["coreosversion"]}}
cd {{cnf["coreosversion"]}}
wget -q https://{{cnf["coreoschannel"]}}.release.core-os.net/amd64-usr/{{cnf["coreosversion"]}}/coreos_production_image.bin.bz2
wget -q https://{{cnf["coreoschannel"]}}.release.core-os.net/amd64-usr/{{cnf["coreosversion"]}}/coreos_production_image.bin.bz2.sig

cd /var/lib/tftpboot/
wget -q https://{{cnf["coreoschannel"]}}.release.core-os.net/amd64-usr/current/coreos_production_pxe.vmlinuz 
wget -q https://{{cnf["coreoschannel"]}}.release.core-os.net/amd64-usr/current/coreos_production_pxe.vmlinuz.sig 
wget -q https://{{cnf["coreoschannel"]}}.release.core-os.net/amd64-usr/current/coreos_production_pxe_image.cpio.gz 
wget -q https://{{cnf["coreoschannel"]}}.release.core-os.net/amd64-usr/current/coreos_production_pxe_image.cpio.gz.sig
chmod -R 777 /var/lib/tftpboot/

# If need, download additional content to usr/share/oem 

cp coreos_production_pxe_image.cpio.gz cpio.gz
gunzip cpio.gz
sed "s/_===CONFIG===_/install-worker.sh/g" usr/share/oem/oem-config.yml > usr/share/oem/cloud-config.yml
find usr | cpio --verbose -o -A -H newc -O cpio
gzip cpio
mv cpio.gz cpioworker.gz

cp coreos_production_pxe_image.cpio.gz cpio.gz
gunzip cpio.gz
sed "s/_===CONFIG===_/install-etcd.sh/g" usr/share/oem/oem-config.yml > usr/share/oem/cloud-config.yml
find usr | cpio --verbose -o -A -H newc -O cpio
gzip cpio
mv cpio.gz cpioetcd.gz

# A separate master image is no longer needed
#
#cp coreos_production_pxe_image.cpio.gz cpio.gz
#gunzip cpio.gz
#sed "s/_===CONFIG===_/install-master.sh/g" usr/share/oem/oem-config.yml > usr/share/oem/cloud-config.yml
#find usr | cpio --verbose -o -A -H newc -O cpio
#gzip cpio
#mv cpio.gz cpiomaster.gz

wget -q https://www.kernel.org/pub/linux/utils/boot/syslinux/syslinux-6.03.tar.gz
tar -zxvf syslinux-6.03.tar.gz
cp syslinux-6.03/bios/com32/chain/chain.c32 .
cp syslinux-6.03/bios/com32/elflink/ldlinux/ldlinux.c32 .
cp syslinux-6.03/bios/com32/lib/libcom32.c32 .
cp syslinux-6.03/bios/com32/libutil/libutil.c32 .
cp syslinux-6.03/bios/core/pxelinux.0 .
cp syslinux-6.03/bios/com32/menu/vesamenu.c32 .
rm -r syslinux-6.03
rm syslinux-6.03.tar.gz
