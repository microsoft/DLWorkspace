# Deployment of DL workspace cluster via USB sticks

This document describes the procedure to build and deploy a small DL workspace cluster via USB sticks. The key procedures are:
  1 [Create Configuration file](configuration/Readme.md)
  * [Build a bootable image](../Build.md) (ISO/docker image) :
     You can directly use Ubuntu ISO image for Ubuntu deployment. Please [build CoreOS ISO image](../Build.md).
  * Burn a USB stick (>=1GB):
     You could use [Rufus](https://www.ubuntu.com/download/desktop/create-a-usb-stick-on-windows) tool recommended by Ubuntu or many other tools to burn .iso to a USB stick. If Rufus is used, please use the following options:
       * Parition scheme: MBR partition scheme for BIOS or UEFI,
       * File system: FAT32,
       * For option "Create a bootable disk using:" select the ISO built in step 2. After selecting the ISO file, please select to use **__DD__** mode, (If you first select to use DD image, make sure to use find all files to locate the ISO image), please do not use the default ISO mode,  
       * Please reconfirm that all data in the USB stick will be destroyed. 
  * Boot each machine with the USB stick, and deploy Kubernetes master, etcd server or worker nodes. 
     You should deploy the exact number of Etcd servers as required in your config.yaml file. 
  * Each machine will be shutdown after deployment. Please make sure to turn on the machine after the successful deployment. 

Knowledge of Linux, CoreOS and Kubernetes will be very helpful to understand the deployment instruction. 
