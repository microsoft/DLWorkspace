# Deployment of DL workspace cluster via USB sticks

This document describes the procedure to build the deployment image for DL workspace cluster. After the configuration file is [created](Configuration.md), in directory 'src/ClusterBootstrap', run:

```
python deploy.py build 
```

1. If you see the question: There is a cluster deployment in './deploy', override the existing ssh key and CA certificates (y/n)?
You have a previous build. Answer "yes" will create a new build, which will overwrite your prior build (and you will lost access to the previous cluster, if you haven't saved relevant configuration.)
Answer "no" will preserve prior cluster information, so you can still access the rebuild cluster using your prior configuration. 
2. Answer "yes" to question "Create ISO file for deployment (y/n)?" to generate the ISO image for USB deployment.
3. Answer "yes" to question "Create PXE docker image for deployment (y/n)?" to generate the docker iamge for PXE deployment. 
You should only need either one of the above option.
