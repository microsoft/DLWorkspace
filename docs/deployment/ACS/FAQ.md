# Frequently Asked Questions (FAQ) for ACS Deployment. 

Please refer to [this](../knownissues/Readme.md) for more general deployment issues. 

## After setup, I cannot visit the deployed DL Workspace portal. 

* Please wait a few minutes after the deployment script runs through to allow the portal container to be pulled and scheduled for execution. 

## I can't execute Spark job on Azure. 

The current default deployment procedure on Azure doesn't deploy HDFS/Spark. So Spark job execution is not available. 

## For 'az login', when I type in the device code, the web page prompt me again for the code. 

It seems that sometime the browser (Edge, Chrome) cache another identity not intended to be used with az login. To get around, please start the browser in (in-private) or (incognito) mode, you may then enter the proper device code. 

## The deployment script returns with error 

    ```
    Deployment failed. {
    "error": {
        "code": "BadRequest",
        "message": "The credentials in ServicePrincipalProfile were invalid...
    ```

    It seems that ACS creation fails from time to time. Please try to rerun the script. If things repeat, please consider to use [Azure Cluster](../Azure/Readme.md) deployment first till we investigate and fix the issue. 

## I have launched a GPU job (e.g., TensorFlow-iPython). However, I am unable to access the endpoint with error 

    ```This site can’t be reached
    k8s-agent-d544f279-0.northcentralus.cloudapp.azure.com refused to connect.
    ```

    We have noticed this endpoint access problem with ACS, particular with GPU jobs. At this moment, we are still investigating what is the cause of the issue. We particularly observe that the endpoint of a CPU job is accessible, while the endpoint of a GPU job is not, even both job are scheduled on the same VM with the same networking rule. 