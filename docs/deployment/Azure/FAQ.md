# Frequently Asked Questions (FAQ) for Azure Cluster Deployment. 

Please refer to [this](../knownissues/Readme.md) for more general deployment issues. 

## After setup, I cannot visit the deployed DL Workspace portal. 

* Please wait a few minutes after the deployment script runs through to allow the portal container to be pulled and scheduled for execution. 

## I can't execute Spark job on Azure. 

The current default deployment procedure on Azure doesn't deploy HDFS/Spark. So Spark job execution is not available. 

## For 'az login', when I type in the device code, the web page prompt me again for the code. 

It seems that sometime the browser (Edge, Chrome) cache another identity not intended to be used with az login. To get around, please start the browser in (in-private) or (incognito) mode, you may then enter the proper device code. 

## I have launched a job (e.g., TensorFlow-iPython-GPU). However, I am unable to access the endpoint with error 

    ```This site can’t be reached
    ....cloudapp.azure.com refused to connect.
    ```

    Please check the docker image of the job you are running. Sometime, the iPython (or SSH server) hasn't been properly started, which caused the endpoint to be not accessible.  

## I notice that my azure command is failing. 

Azure CLI may time out after inactivity. You may need to re-login via 'az login'. 

## Common configuration errors. 

* "merge_config( config["azure_cluster"], tmpconfig["azure_cluster"][config["azure_cluster"]["cluster_name"]], verbose )"
  Please check if the cluster_name used in azure_cluster is the same as the DL workspace cluster name.