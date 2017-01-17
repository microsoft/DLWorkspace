# Deployment of DL workspace cluster via USB sticks

This document describes the procedure to build and deploy a small DL workspace cluster via USB sticks. The key procedures are:
  1. [Create Configuration file](Configuration.md)
  2. Build a bootable USB image via:
     ```
     python deploy.py build 
     ```
  3. Burn a USB stick:
     You could use [Rufus](https://www.ubuntu.com/download/desktop/create-a-usb-stick-on-windows) recommended by Ubuntu or many other tools to burn .iso to a USB stick. 
  4. Boot each machine with the USB stick, to deploy Kubernetes master, etcd server or worker nodes. 
     You should deploy the exact number of Etcd servers as required in your config.yaml file.   

Knowledge of Linux, CoreOS and Kubernetes will be very helpful to understand the deployment instruction. 
