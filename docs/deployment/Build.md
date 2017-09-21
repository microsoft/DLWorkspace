# Build ISO (for USB) or docker image (PXE) for DL workspace deployment.

The following constructs cluster unique information (e.g., cluster_ID) that will be used for further cluster deployment. 
```
python deploy.py -y build 
```

1. Option "-y" automatically answer yes to all build questions. Without the option, you will be asked the follow questions. 
2. Question: There is a cluster deployment in './deploy', do you want to keep the existing ssh key and CA certificates (y/n)?
  You have a previous build. Answer "no" will create a new build, which will overwrite your prior build (and you will lost SSH key and other parameter used to access to the previous cluster, if you haven't saved relevant configuration.)
  Answer "yes" will preserve prior cluster information, which allows you to build a new deployment image, but keep the cluster configuration. 

* To build ISO image for CoreOS USB/DVD deployment, use:
```
python deploy.py -y build iso-coreos
```

* To build PXE image for CoreOS deployment, use:
```
python deploy.py -y build pxe-coreos
```

* To build PXE image for Ubuntu deployment, use:
```
python deploy.py -y build pxe-ubuntu
```

We simply use standard Ubuntu ISO image for Ubuntu USB/DVD deployment. 