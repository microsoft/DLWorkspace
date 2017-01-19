# Use PXE server to deploy DL workspace cluster. 

This document describes the procedure to deploy DL workspace cluster via PXE server. **__The procedure will automatically wipe out the system disk and deploy a CoreOS image of DL workspace cluster__** to all machines that are on the same subnet and served by the PXE server. Please proceed with caution. 

1. [Create Configuration file](Configuration.md)

2. [Build a bootable image](Build.md).

3. Put the docker image on PXE server. 

4. Run docker image:

  ```
  docker run -ti --net=host [DOCKER_IMAGE] bash
  ```

5. Select network interface for PXE server to operate on (eth0 if only one internet interface):
  ```
  vi /etc/default/isc-dhcp-server
  ```

6. Edit the Tftp configuration file to control which image to be deployed. 

  ```
  vi /tftp/pxelinux.cfg/default
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

  Once PXE server has been started, any node that are booted on the same VLAN of the PXE server will have its system drive wiped out, and deployed for a Kubernetes master, etcd server, or worker node. Thus, please proceed with caution. 
  
