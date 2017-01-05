# ETCD service deployment

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

6. connect worker nodes to the private network, boot worker nodes using network boot option. 
Wait until the worker nodes shutdown automatically. 
Disconnect worker nodes from the private network. 
Restart the worker nodes.
Done: the worker nodes will automatically register themselves to kubernetes cluster and install necessary drivers. 

# WebUI service deployment
