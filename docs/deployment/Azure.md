# Deploy DL workspace cluster on Azure. 

This document describes the procedure to deploy DL workspace cluster on Azure. We are still improving the deployment procedure on Azure. Please contact the authors if you have encounter deployment issue. 

1. Please create Configuration file with single line of your cluster name. The cluster name should be unique, only with lower characters or numbers.

```
cluster_name: [your cluster name]
```

2. Initial cluster and generate certificates and keys:
```
./deploy.py -y build
```
3. Create Azure Cluster:
```
./az_tools.py create
```
 
4. Run Azure deployment script block:
  ```
  ./deploy.py --verbose scriptblocks azure 
  ```
  After the script completes execution, you may still need to wait for a few minutes so that relevant docker images can be pulled to the target machine for execution. You can then access your cluster at:
  ```
  http://machine1.westus.cloudapp.azure.com/
  ```
  where machine1 is your azure infrastructure node. (you may get the address by ./deploy.py display)




  The script block execute the following command in sequences: (you do NOT need to run the following commands if you have run step 4)
  1. Setup basic tools on the Ubuntu image. 
  ```
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

  4. Build and deploy jobmanager, restfulapi, and webportal. Mount storage.
  ```
  ./deploy.py docker push restfulapi
  ./deploy.py docker push webui
  ./deploy.py webui
  ./deploy.py mount
  ./deploy.py kubernetes start jobmanager restfulapi webportal
  ```

6. If you run into a deployment issue, please check [here](Deployment_Issue.md) first. 


