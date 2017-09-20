# Deploy DL Workspace cluster on Azure Container Service (ACS)

This document describes the procedure to deploy DL Workspace cluster on ACS. We are still improving the deployment procedure on ACS. Please contact the authors if you encounter any issues. 

1. Follow [this document](../../DevEnvironment/Readme.md) to setup the dev environment of DLWorkspace. Login to your Azure subscription on your dev machine via:

```
az login
```

2. Please [configure](configure.md) your ACS cluster.

3. Set proper [authentication](../authentication.md).

4. Running deployment script on the dev machine under src/ClusterBootstrap, as follows:

```
./deploy.py acs
```

The deployment script executes the following commands in sequence.

    1. Setup basic K8S cluster on ACS
    ```
    ./deploy.py acs deploy
    ```

    2. Label nodels and deploy services:
    ```
    ./deploy.py acs postdeploy
    ```

    3. Mount storage on nodes:
    ```
    ./deploy.py acs storagemount
    ```

    4. Install GPU drivers on nodes (if needed):
    ```
    ./deploy.py acs gpudrivers
    ```

    5. Install network plugin
    ```
    ./deploy.py acs freeflow
    ```

    6. Build needed docker images and configuration files for restfulapi, jobmanager, and webui
    ```
    ./deploy.py acs bldwebui
    ```

    7. Start DLWorkspace pods
    ```
    ./deploy.py acs restartwebui
    ```

5. If you run into a deployment issue, please check [here](FAQ.md) first. 
