# Deployment of DL workspace cluster

This document describes the procedure to build and deploy a DL workspace cluster. You will need to build and deploy the following nodes: 
  1. One kubernetes master server
  2. One etcd server (or etcd cluster with multiple nodes for redundant operation)
  3. A web server to host kubelet configuration files and certificates generation service
  4. Multiple kubernete work nodes for running the job.

Basic knowledge of Linux and CoreOS will be very helpful to follow the deployment instruction.   

## Deploy Kubernetes master server, etcd, web servers (these servers will then deploy all other servers in the cluster)

We describe the steps to install and deploy a customized Kubernetes cluster. It is possible to install master server, etcd, and web server on a single machine. Using multiple etcd server does provide the benefit of redundancy in case one of the server fails. 

### Base CoreOS deployment. 

This section describes the process of deploying a base CoreOS image through USB stick. In production environment, there may be other more efficient mechanisms to deploy the CoreOS images to machines. 

Please prepare a Cloud config file that will be used to bootstrap the deployed CoreOS machine. A sample config file is provided at: src/ClusterBootstrap/CoreOSConfig/pxe-kubemaster.yml.template. Please copy the file to pxe-kubemaster.yml, and fill in username, password, and SSH key information according to instruction at: https://coreos.com/os/docs/latest/cloud-config.html. Then, host the pxe-kubemaster.yml to a web service that you control. In the follows, let us assume that the host URL as [CLOUD_CONFIG_URL]. Please note that URL shortcut service such as aka.ms may not work in the CoreOS boot environment, you may need to write down and use the full [CLOUD_CONFIG_URL].

Download a booting CoreOS ISO according to instruction at: https://coreos.com/os/docs/latest/booting-with-iso.html, and put the ISO on a USB drive. Then, boot from the CoreOS USB drive.

To access Internet from the CoreOS boot environment, you may need to edit /etc/resolv.conf file, and add a public name server, e.g., 

```
nameserver 8.8.8.8
```

Then, you can download the cloud config file from [CLOUD_CONFIG_URL], and the install the CoreOS boot image via:

```
sudo coreos-install -d /dev/sda -C stable -c [CLOUD_CONFIG_URL]
```

Once installation is completed, please use 'ifconfig' to print the IP address of the machine. The IP addresses are used later to access the deployed CoreOS machine. After success installation, you can unplug the USB drive and reboot the machine via:

```
sudo reboot
```

### [Optional] Register the machine with DNS service. 

This section is specific jjto Microsoft Internal setup. You may use the service at http://namesweb/ to self generate a DNS record for your installed machine. If this machine has a prior DNS name (e.g., a prior Redmond domain machine), you may need to first delete the dynamic DNS record of the prior machine, and then add your machine. If you machine has multiple IP address, please be sure to add both IP addresses to the DNS record.  

### Generate Certificates for API server & etcd server 

1. Copy src\ClusterBootstrap\ssl\openssl-apiserver.cnf.template to openssl-apiserver.cnf, and edit the configuration file:
  * add DNS name for the kubernetes master. 
    * For DNS name, add DNS.5, DNS.6 for the new DNS name 
  * Add IP addresses of the kubernete master. 
    * Replace ${K8S_SERVICE_IP} by the IP of kubernetes service, default to "10.3.0.1"
    * replace ${MASTER_HOST} by the host IP. "IP.3, IP.4..." can be added for multiple NIC. 
2. modify src\ClusterBootstrap\ssl\openssl-etcd.cnf
3. run gen_certs.sh to generate certs

    ```
    cd src/ClusterBootstrap/ssl/
    ./gen_certs.sh
    ```

## Building of docker images. 

The first step is to build the various docker images that is used in DL workspace. The procedures are:

1. build docker image to host web service
  ```
  docker build -t mlcloudreg.westus.cloudapp.azure.com:5000/dlworkspace/httpservice:dlws-c1-web deploy/web-docker/
  docker push mlcloudreg.westus.cloudapp.azure.com:5000/dlworkspace/httpservice:dlws-c1-web 
  ```
  
2. run the docker image on the web server
  ```
  docker run -d -p 80:80 -p 5000:5000 mlcloudreg.westus.cloudapp.azure.com:5000/dlworkspace/httpservice:dlws-c1-web
  ```

3. build pxe image
    ```
    docker build -t mlcloudreg.westus.cloudapp.azure.com:5000/dlworkspace/pxeserver:dlws-c1-web pxe-kubelet/
    docker push mlcloudreg.westus.cloudapp.azure.com:5000/dlworkspace/pxeserver:dlws-c1-web
    ``` 

Please prepare/gather the following information. If you are working in a managed computer system, e.g., in a corporate network, you may need to work with your IT administrator to get the following information:
   1. Static IP of kubernetes master, username with sudo permission, (optional) DNS name
   2. Static IP of web server,  username with sudo permission, (optional) DNS name
   3. Static IP of etcd server, username with sudo permission, (optional) DNS name
   4. The kubernetes pod ip range, default is: 10.2.0.0/16
   5. The kubernetes service ip range, default is: 10.3.0.0/16 
   6. Build kubernetes binary, (e.g. kubernetes/_output/bin/kubelet), you may use an existing kubernete distribution. Please refer to http://kubernetes.io/docs/getting-started-guides/binary_release/#prebuilt-binary-release for details.  
   7. Ssh certificates which allow no-password login to kubernetes master and etcd. Please refer to 
https://linuxconfig.org/passwordless-ssh on generating ssh keys and use them for subsequent login.   
   8. Please prepare src/ClusterBootstrap/config.yaml from the config.yaml.template in the same directory. 
   
   Make a copy of the config.yaml.template file to config.yaml, 
   
     ```
     curl -w "\n" 'https://discovery.etcd.io/new?size=1'
     ```
     output:
     ```
     https://discovery.etcd.io/2074363dd5a9efacae8c956240ca7794
     ```
     Note: change "size=1" to the actual etcd cluster size. and replace the place holder {{discovery_url}} in config.yaml file.  

prepare config.yaml file from 
 
   
   


# Generate deployment files

 ```
 cd src/ClusterBootstrap
 python deploy.py
 ```
 the script generates configuration files and deploy the etcd and kubernetes master. 



4. run pxe server docker image on a laptop (or server)

 ideally, pxe server should have two network interface, we use eth0 in private network and eth1 in public network.  

 1. config static ip on eth0

   sudo vi /etc/network/interfaces
   ```
   auto eth0
   iface eth0 inet static
   address 192.168.1.20
   netmask 255.255.255.0
   ```
   sudo reboot

 2. pull and run docker image
   ```
   docker pull mlcloudreg.westus.cloudapp.azure.com:5000/dlworkspace/pxeserver:dlws-c1-web

   docker run -ti --net=host mlcloudreg.westus.cloudapp.azure.com:5000/dlworkspace/pxeserver:dlws-c1-web bash
   ```

 3. prepare data

   ```
   /copy_html_data.sh
   ```

 4. select network interface for dhcp service
   ```
   vi /etc/default/isc-dhcp-server
   ```

 5. start service
   ```
   start_pxe_service.sh
   ```

 6. deploy worker nodes
   connect worker nodes to the private network, boot worker nodes using network boot option. 
   Wait until the worker nodes shutdown automatically. 
   Disconnect worker nodes from the private network. 
   Restart the worker nodes.
   Done: the worker nodes will automatically register themselves to kubernetes cluster and install necessary drivers. 

