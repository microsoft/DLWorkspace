# Deployment of DL workspace cluster

This document describes the procedure to build and deploy a DL workspace cluster. You will need to build and deploy the following nodes: 
  1. One Kubernetes master server,
  2. Etcd server (or etcd cluster with multiple nodes for redundant operation), 
  3. API servers, 
  4. Web server to host kubelet configuration files and certificates generation service,
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

This section is specific to Microsoft Internal setup. You may use the service at http://namesweb/ to self generate a DNS record for your installed machine. If this machine has a prior DNS name (e.g., a prior Redmond domain machine), you may need to first delete the dynamic DNS record of the prior machine, and then add your machine. If you machine has multiple IP address, please be sure to add both IP addresses to the DNS record.  

### Generate Certificates for API server & etcd server 

Go to folder 'src/ClusterBootstrap/ssl', and perform the following operations:

1. Copy openssl-apiserver.cnf.template to openssl-apiserver.cnf, and edit the configuration file:
  * Add DNS name for the kubernetes master. 
    * For DNS name, add DNS.5, DNS.6 for the new DNS name 
  * Add IP addresses of the kubernete master. 
    * Replace ${K8S_SERVICE_IP} by the IP of kubernetes service, default to "10.3.0.1"
    * replace ${MASTER_HOST} by the host IPs. If there are multiple IP address of the deployed machine, they should all be added here, e.g., via another entry of "IP.3". 
2. Copy openssl-etcd.cnf.template to openssl-etcd.cnf, and edit the configuration file:
  * Add DNS name for the etcd server. [similar to above] 
  * Add IP addresses of the etcd server. [similar to above]h
3. run 'gencerts.sh' to generate certs

### Modify configuration file for the deployed docker container. 

Go to directory 'src/ClusterBookstrap', and copy 'config.yaml.template' to 'config.yaml'. Edit the configuration file with the follwoing information:

1. Generate a new Etcd discover ID, by visiting webpage 'https://discovery.etcd.io/new?size=1'. For example, you may use:
     ```
     curl -w "\n" 'https://discovery.etcd.io/new?size=1'
     ```
If your etcd cluster has multiple nodes, please change "size=1" to the actual etcd cluster size. 
Replace the place holder {{discovery_url}} in config.yaml file with the output of the discovery service, e.g., 'https://discovery.etcd.io/fec3b8145de4e19c2812ef64b542bc29'.  
2. Replace all entries of '{{kubernete_master_dnsname_or_ip}}' with either the DNS name or one of the IP addresses of kubernetes master. This will be used for bootstrapping kubernetes master [deploying kubernete configuration and certificate]. 
3. Replace '{{user_at_kubernete_master}}' with the authorized user during CoreOS installation. 
4. Replace '{{user_at_etcd_server}}' with the authorized user during CoreOS installation. 
5. Replace '{{apiserver_dnsname_or_ip}}' with either the DNS name or one of the IP addresses of the etcd server. 
6. Generate ssh key for access the kubernete cluster via following command. 
'''
ssh-keygen -t rsa -b 4096
''' 
You may want to store the generated key under the current directory, instead of default ('~/.ssh'). 
This key is used just in the kubernete deployment process. Therefore, you can discard the ssh key after the entire deployment procedure has been completed. 
8. Replace {{apiserver_password,apiserver_username,apiserver_group}} with a password and username that is used to adminstrating API server. For example, if you use "helloworld,adam,1000", then the API server can be administered through username adam, and password helloworld. 
9. Build kubernete binary. 
DL Workspace needs a multigpu-aware Kubernete build, which is currently in our private branch. For the moment, please refer to document docs/DevEnvironment/Kubernetes.md on how to build the Kubernete build needed. We are in the process of simplifying this step, to make the required Kubernetes build more simple for deployment. 
10. run 'deploy.py' to deploy kubernete masters, etcd servers, and API servers. 


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

