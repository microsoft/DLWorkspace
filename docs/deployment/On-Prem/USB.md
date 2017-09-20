# Deployment of DL workspace cluster via USB sticks

This document describes the procedure to build and deploy a small DL workspace cluster via USB sticks. The key procedures are:
  1. [Create Configuration file](configuration/Readme.md)
  2. [Build a bootable image](../Build.md) (ISO/docker image) :
     You can directly use Ubuntu ISO image for Ubuntu deployment. Please [build CoreOS ISO image](../Build.md).
  3. Burn a USB stick (>=1GB):
     You could use [Rufus](https://www.ubuntu.com/download/desktop/create-a-usb-stick-on-windows) tool recommended by Ubuntu or many other tools to burn .iso to a USB stick. If Rufus is used, please use the following options:
       * Parition scheme: MBR partition scheme for BIOS or UEFI,
       * File system: FAT32,
       * For option "Create a bootable disk using:" select the ISO built in step 2. After selecting the ISO file, please select to use **__DD__** mode, (If you first select to use DD image, make sure to use find all files to locate the ISO image), please do not use the default ISO mode,  
       * Please reconfirm that all data in the USB stick will be destroyed. 
  4. Boot each machine with the USB stick. For CoreOS deployment, select Kubernetes master, etcd server or worker nodes. For Ubuntu deployment, the master, etcd and worker node are specified through the config.yaml file. 
  5. Each machine will be shutdown after deployment. Please make sure to turn on the machine after the successful deployment. 

Knowledge of Linux, CoreOS and Kubernetes will be very helpful to understand the deployment instruction. 
