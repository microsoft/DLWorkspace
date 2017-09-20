# Deploy DL Workspace cluster on Azure. 

This document describes the procedure to deploy DL Workspace cluster on Azure. We are still improving the deployment procedure on Azure. Please contact the authors if you have encounter deployment issue. 

Please note that the procedure below doesn't deploy HDFS/Spark on DLWorkspace cluster on Azure. So Spark job execution is not available on Azure Cluster. 

1. Follow [this document](../../DevEnvironment/Readme.md) to setup the dev environment of DLWorkspace. Login to your Azure subscription on your dev machine via:

```
az login
```

2. Please [configure](configure.md) your azure cluster. 

3. Set proper [authentication](../authentication.md).

4. Initial cluster and generate certificates and keys:
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

  The script block execute the following command in sequences: (you do NOT need to run the following commands if you have run step 5)
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

8. If you run into a deployment issue, please check [here](FAQ.md) first. 


