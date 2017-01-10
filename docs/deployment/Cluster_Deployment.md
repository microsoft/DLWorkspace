# Generate Certificates
1. modify src\ClusterBootstrap\ssl\openssl-apiserver.cnf
  * add DNS name and IP for the kubernetes master. 
    * For DNS name, add DNS.5, DNS.6 for the new DNS name 
  * replace ${K8S_SERVICE_IP} by the service ip, e.g. "10.3.0.1"
  * replace ${MASTER_HOST} by the host IP. "IP.3, IP.4..." can be added for multiple NIC. 
2. modify src\ClusterBootstrap\ssl\openssl-etcd.cnf
3. run src/ClusterBootstrap/ssl/gen_certs.sh to generate certs


# ETCD service deployment




# ETCD service deployment (Multi-nodes)
1. Create a discovery url
  ```
  curl -w "\n" 'https://discovery.etcd.io/new?size=3'
  ```
  output:
  ```
  https://discovery.etcd.io/2074363dd5a9efacae8c956240ca7794
  ```
  Note: change "size=3" to the actual etcd cluster size. and replace the place holder {{discovery_url}} in config.yaml file.  

2. to be continued. 

# Kubernetes master deployment


# Worker nodes deployment

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
  docker pull mlcloudreg.westus.cloudapp.azure.com:5000/pxe-coreos:kubelet

  docker run -ti --net=host mlcloudreg.westus.cloudapp.azure.com:5000/pxe-coreos:kubelet bash
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

# WebUI service deployment
