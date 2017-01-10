# General Information
The system needs:
  1. one kubernetes master server
  2. one etcd server (or etcd cluster with multiple nodes)
  3. a web server to host kubelet configuration files and certificates generation service
note: 2 and 3 could be Azure VM. 

Please prepare and plan the following information:
   1. kubernetes master IP, username with sudo permission, (optional) DNS name
   2. web server IP,  username with sudo permission, (optional) DNS name
   3. etcd server IP, username with sudo permission, (optional) DNS name
   4. plan the kubernetes pod ip range, default: 10.2.0.0/16
   5. plan the kubernetes service ip range, default: 10.3.0.0/16 
   6. compile kubernetes source code, get kubelet binary file, (e.g. kubernetes/_output/bin/kubelet)
   7. ssh certificates which allow no-password login to kubernetes master and etcd
   8. etcd discovery url
   
     ```
     curl -w "\n" 'https://discovery.etcd.io/new?size=3'
     ```
     output:
     ```
     https://discovery.etcd.io/2074363dd5a9efacae8c956240ca7794
     ```
     Note: change "size=3" to the actual etcd cluster size. and replace the place holder {{discovery_url}} in config.yaml file.  

prepare config.yaml file from config.yaml.template
 
   
   
# Generate Certificates
1. modify src\ClusterBootstrap\ssl\openssl-apiserver.cnf
  * add DNS name and IP for the kubernetes master. 
    * For DNS name, add DNS.5, DNS.6 for the new DNS name 
  * replace ${K8S_SERVICE_IP} by the service ip, e.g. "10.3.0.1"
  * replace ${MASTER_HOST} by the host IP. "IP.3, IP.4..." can be added for multiple NIC. 
2. modify src\ClusterBootstrap\ssl\openssl-etcd.cnf
3. run gen_certs.sh to generate certs

    ```
    cd src/ClusterBootstrap/ssl/
    ./gen_certs.sh
    ```

# Generate deployment files

 ```
 cd src/ClusterBootstrap
 python deploy.py
 ```
 the script generates configuration files and deploy the etcd and kubernetes master. 


# Worker nodes deployment
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

