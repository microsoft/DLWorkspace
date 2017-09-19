# Use PXE server to deploy DL workspace cluster. 

This document describes the procedure to deploy DL workspace cluster via PXE server. **__The procedure will automatically wipe out the system disk and deploy a CoreOS image of DL workspace cluster__** to all machines that are on the same subnet and served by the PXE server. Please proceed with caution. 

1. [Create Configuration file](configuration/Readme.md)

2. [Build a bootable image](Build.md).

3. Put the docker image on PXE server. 
  ```
  ./deploy.py build pxe
  ```
  build PXE server for CoreOS deployment. 
  ```
  ./deploy.py build pxe-ubuntu
  ```
  build PXE server for Ubuntu deployment (currently 16.04.2)

4. Run docker image:

  ```
  docker run --privileged --net=host -ti [DOCKER_IMAGE] bash
  ```

5. [CoreOS PXE Server]Select network interface for PXE server to operate on (eth0 if only one internet interface):
  ```
  vi /etc/default/isc-dhcp-server
  ```

6. [CoreOS PXE Server] Edit the Tftp configuration file to control which image to be deployed. 

  ```
  vi /var/lib/tftpboot/pxelinux.cfg/default
  ```
  
  You may want to modify the following parameters:
  
  1. TIMEOUT: the timeout value during which the bootloader will wait for keyboard input before it proceeds to deploy CoreOS image
  2. ONTIMEOUT and DEFAULT: change both to
    1. coreosmaster: to deploy Kubernetes master 
    2. coreosetcd: to deploy Kubernetes etcd servers
    3. coreosworker: to deploy Kubernetes worker nodes

7. Start PXE server
  ```
  start_pxe_service.sh
  ```

8. [CoreOS PXEServer] Once PXE server has been started, any node that are booted on the same VLAN of the PXE server will have its system drive wiped out, and deployed for a Kubernetes master, etcd server, or worker node. Thus, please proceed with caution. 

9. [Ubuntu PXE Server] Ubuntu will default to boot to local drive, and you will need to select deploy Ubuntu server to deploy the server image. 

10. [Ubuntu PXE Server] 
   ```
   .\deploy.py sshkey install
   ```
   Ubuntu setup need to first insert sshkey into target machine.
  
11. Some known issues:
   1. If a machine has multiple network interface, and uses one network interface to reach PXE server, and another to reach internet, it is **__sometime__** necessary to disconnect the network to the PXE server at the end of the installation to correctly routed internet access. 
   2. By design, at the end of the deployment process, all nodes will be automatically shutdown. If a certain node is still up, the node has failed the deployment. (We observe that many time the node fails as it can't download needed docker image from the network. )
