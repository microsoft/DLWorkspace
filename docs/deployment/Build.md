# Build ISO (for USB) or docker image (PXE) for DL workspace deployment.

This document describes the procedure to build the deployment image for DL workspace cluster. After the configuration file is [created](configuration/Readme.md), in directory 'src/ClusterBootstrap', run:

```
python deploy.py -y build 
```

1. Option "-y" automatically answer yes to all build questions. Without the option, you will be asked the follow questions. 
2. Question: There is a cluster deployment in './deploy', do you want to keep the existing ssh key and CA certificates (y/n)?
  You have a previous build. Answer "no" will create a new build, which will overwrite your prior build (and you will lost SSH key and other parameter used to access to the previous cluster, if you haven't saved relevant configuration.)
  Answer "yes" will preserve prior cluster information, which allows you to build a new deployment image, but keep the cluster configuration. 
2. Answer "yes" to question "Create ISO file for deployment (y/n)?" to generate the ISO image for USB deployment.
3. Answer "yes" to question "Create PXE docker image for deployment (y/n)?" to generate the docker iamge for PXE deployment. 
There is need to choose one of the above option, though in default, both ISO and PXE docker images will be built. 
