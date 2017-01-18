# Deployment of DL workspace cluster via USB sticks

This document describes the procedure to build and deploy a small DL workspace cluster via USB sticks. The key procedures are:
  1. [Create Configuration file](Configuration.md)
  2. Build a bootable USB image via:
     ```
     python deploy.py build 
     ```
  3. Burn a USB stick (>=1GB):
     You could use [Rufus](https://www.ubuntu.com/download/desktop/create-a-usb-stick-on-windows) tool recommended by Ubuntu or many other tools to burn .iso to a USB stick. If Rufus is used, please use the following options:
       * Parition scheme: MBR partition scheme for BIOS or UEFI,
       * File system: FAT32,
       * Create a bootable disk using: select the ISO built in step 2, 
       * Write USB in **__DD__** mode, please do not write in the default ISO mode,  
       * Please reconfirm that all data in the USB stick will be destroyed. 
  4. Boot each machine with the USB stick, to deploy Kubernetes master, etcd server or worker nodes. 
     You should deploy the exact number of Etcd servers as required in your config.yaml file. 
  5. Each machine will be shutdown after deployment. Please make sure to turn on the machine after the successful deployment. 

Knowledge of Linux, CoreOS and Kubernetes will be very helpful to understand the deployment instruction. 
