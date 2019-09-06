# Deploy DL Workspace cluster on Azure. 

This document describes the procedure to deploy a DL Workspace cluster on Azure. With autoscale enabled DL Workspace, VM will be created (and released) on demand when you launch DL jobs ( e.g., TensorFlow, Pytorch, Caffe2), thus save your money in operation.

Please note that the procedure below doesn't deploy HDFS/Spark on DLWorkspace cluster on Azure (Spark job execution is not available on Azure Cluster).

Prerequisite steps:
First require the manager to add you into a subscription group., then either 
1. go to that group from Azure Portal and add ubuntu server from resources, this virtual server is your devbox, or 
2. if you have a physical machine, install ubuntu server system(18.04) on that and use it as your devbox
then use the devbox to deploy node on cloud.

Workflow:
1. Please [configure](configure.md) your azure cluster. Put config.yaml under src/ClusterBootstrap

2. Change directory to src/ClusterBootstrap on devbox, and install prerequisite packages:
```
cd src/ClusterBootstrap/ 
sudo ./install_prerequisites.sh
```
3. Login to Azure, setup proper subscription and confirm
```
SUBSCRIPTION_NAME="<subscription name>" 
az login
az account set --subscription "${SUBSCRIPTION_NAME}" 
az account list | grep -A5 -B5 '"isDefault": true'
```
Configure your location, should be the same as you specified in config.yaml file:
```AZ_LOCATION="<your location>"```
Execute this command, log out(exit) and log in back
```sudo usermod -aG docker zhe_ms```
4. Initiate cluster and generate certificates and keys:
```
./deploy.py -y build
```

5. Create Azure Cluster:
```
./az_tools.py create
```

6. Generate cluster config file:
```
./az_tools.py genconfig 
```

Please note that if you are not Microsoft user, you should remove the 
 
7. Run Azure deployment script block:
  ```
  ./deploy.py --verbose scriptblocks azure 
  ```
  After the script completes execution, you may still need to wait for a few minutes so that relevant docker images can be pulled to the target machine for execution. You can then access your cluster at:
  ```
  http://machine1.westus.cloudapp.azure.com/
  ```
  where machine1 is your azure infrastructure node. (you may get the address by ./deploy.py display)

  This command sequetially execute following steps:
  1. Setup basic tools on VM and on the Ubuntu image. 
  ```
  ./deploy.py runscriptonall ./scripts/prepare_vm_disk.sh
  ./deploy.py runscriptonall ./scripts/prepare_ubuntu.sh
  ```

  2. Deploy etcd/master and workers. 
  ```
  ./deploy.py -y deploy
  ./deploy.py -y updateworker
  ```

  3. Label nodels and deploy services:
  ```
  ./deploy.py -y kubernetes labels
  ```

  4. Start Nvidia device plugins:
  ```
  ./deploy.py kubernetes start nvidia-device-plugin
  ```

  5. Build and deploy jobmanager, restfulapi, and webportal. Mount storage.
  ```
  ./deploy.py webui
  ./deploy.py docker push restfulapi
  ./deploy.py docker push webui
  ./deploy.py mount
  ./deploy.py kubernetes start jobmanager restfulapi webportal
  ```

8.  Manually connect to the infrastructure/master node:
  ```./deploy.py connect master```
  On master node(log in from devbox by ./deploy.py connect master), manually add ```"Grafana": "",``` to /etc/WebUI/userconfig.json, under "Restapi" entry.
  Restart the WebUI docker:
  Login to the master node, and use
  ```docker ps | grep web``` 
  to get the ID corresponding to Web UI, then restart that docker image: 
  ```docker rm -f <WebUI ID>```
  Wait for minutes for it to restart (can follow by using ```docker logs --follow <WebUI ID>```) and visit the infra node from web browser.

9. If you run into a deployment issue, please check [here](FAQ.md) first.