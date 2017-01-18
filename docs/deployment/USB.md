# Deployment of DL workspace cluster via USB sticks

This document describes the procedure to build and deploy a small DL workspace cluster via USB sticks. The key procedures are:
  1. [Create Configuration file](Configuration.md)
  2. Build a bootable USB image via:
     ```
     python deploy.py build 
     ```
       1. If you see the question: There is a cluster deployment in './deploy', override the existing ssh key and CA certificates (y/n)?
       You have a previous build. Answer "yes" will create a new build, which will overwrite your prior build (and you will lost access to the previous cluster, if you haven't saved relevant configuration.)
       Answer "no" will preserve prior cluster information, so you can still access the rebuild cluster using your prior configuration. 
       2. Answer "yes" to question "Create ISO file for deployment (y/n)?" to generate the ISO image for USB deployment.
       3. Answer "yes" to question "Create PXE docker image for deployment (y/n)?" to generate the docker iamge for PXE deployment. 
       You should only need either one of the above option.
  3. Burn a USB stick (>=1GB):
     You could use [Rufus](https://www.ubuntu.com/download/desktop/create-a-usb-stick-on-windows) tool recommended by Ubuntu or many other tools to burn .iso to a USB stick. If Rufus is used, please use the following options:
       * Parition scheme: MBR partition scheme for BIOS or UEFI,
       * File system: FAT32,
       * For option "Create a bootable disk using:" select the ISO built in step 2. After selecting the ISO file, please select to use **__DD__** mode, (If you first select to use DD image, make sure to use find all files to locate the ISO image), please do not use the default ISO mode,  
       * Please reconfirm that all data in the USB stick will be destroyed. 
  4. Boot each machine with the USB stick, to deploy Kubernetes master, etcd server or worker nodes. 
     You should deploy the exact number of Etcd servers as required in your config.yaml file. 
  5. Each machine will be shutdown after deployment. Please make sure to turn on the machine after the successful deployment. 

Knowledge of Linux, CoreOS and Kubernetes will be very helpful to understand the deployment instruction. 
