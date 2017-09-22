# Bootable USB for CoreOS

This document describes the procedures to download and build a bootable USB for CoreOS. We use the information on [here](http://bencane.com/2013/06/12/mkisofs-repackaging-a-linux-install-iso/).

1. Download a latest stable CoreOS ISO via.

  `wget https://stable.release.core-os.net/amd64-usr/current/coreos_production_iso_image.iso`

2. Mount the downloaded ISO on '/mnt/linux'.

  `sudo mkdir -p /mnt/linux`
  `sudo mount -o loop [DOWNLOADED_ISO] /mnt/linux`

3. Copy the content to a directory, so that we can add the Cloud Configuration file, which has the root username, password and ssh key. 

  `cd /mnt/`
  `tar -cvf - linux | (cd /var/tmp/ && tar -xf - )`

4. Add configuration file. 
   Assuming that you added the file under directory '/config'.
5. Repackage the directory into a new bootable ISO file. 

  `mkisofs -o [DISK_IMAGE_NAME].iso -b isolinux/isolinux.bin -c isolinux/boot.cat -no-emul-boot -boot-load-size 4 -boot-info-table -J -R -V [Your Disk Name Here] /var/tmp/linux`
6. Burn Bootable ISO. 

  Please follow [instructions](https://www.ubuntu.com/download/desktop/create-a-usb-stick-on-windows) to burn a bootable USB.

7. Once booted into the USB, the coreos image at /coreos/cpio.gz will be loaded into memory and expanded into a filesystem. To enable the access to your customized USB content, you will need to further mount the USB, as:
  `mount /dev/sde /mnt`
  CoreOS will name your harddrive as /dev/sda, /dev/sdb, etc.. The last one (extra one) is the USB stick, which you should mount. 
