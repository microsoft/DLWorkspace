# Frequently Asked Questions (FAQ) for ACS Deployment. 

Please refer to [this](../knownissues/Readme.md) for more general deployment issues. 

## After setup, I cannot visit the deployed DL Workspace portal. 

* Please wait a few minutes after the deployment script runs through to allow the portal container to be pulled and scheduled for execution. 

## I can't execute Spark job on Azure. 

The current default deployment procedure on Azure doesn't deploy HDFS/Spark. So Spark job execution is not available. 

## The deployment script returns with error 

    ```
    Deployment failed. {
    "error": {
        "code": "BadRequest",
        "message": "The credentials in ServicePrincipalProfile were invalid...
    ```

    It seems that ACS creation fails from time to time. Please try to rerun the script. If things repeat, please consider to use [Azure Cluster](../Azure/Readme.md) deployment first till we investigate and fix the issue. 