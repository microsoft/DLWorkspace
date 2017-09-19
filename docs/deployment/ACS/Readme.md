# Deploy DL Workspace cluster on Azure Container Service (ACS)

This document describes the procedure to deploy DL Workspace cluster on ACS. We are still improving the deployment procedure on ACS. Please contact the authors if you encounter any issues. 

## Follow [this document](../DevEnvironment/README.md) to setup the dev environment of DLWorkspace. Login to your Azure subscription on your dev machine via:

```
az login
```

## Please [configure](configure.md) your ACS cluster. 

## Running deployment script on the dev machine under src/ClusterBootstrap, as follows:

```
./deploy.py acs
```

The deployment script executes the following commands in sequence.

* Setup basic K8S cluster on ACS
```
./deploy.py acs deploy
```

* Label nodels and deploy services:
```
./deploy.py acs postdeploy
```

* Mount storage on nodes:
```
./deploy.py acs storagemount
```

* Install GPU drivers on nodes (if needed):
```
./deploy.py acs gpudrivers
```

* Install network plugin
```
./deploy.py acs freeflow
```

* Build needed docker images and configuration files for restfulapi, jobmanager, and webui
```
./deploy.py acs bldwebui
```

* Start DLWorkspace pods
```
./deploy.py acs restartwebui
```

## If you run into a deployment issue, please check [here](FAQ.md) first. 
