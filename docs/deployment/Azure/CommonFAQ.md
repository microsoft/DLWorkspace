# Frequently Asked Questions (FAQ) for Azure Cluster Deployment. 

Please refer to [this](../knownissues/Readme.md) for more general deployment issues. 

## After setup, I cannot visit the deployed DL Workspace portal. 

* Please wait a few minutes after the deployment script runs through to allow the portal container to be pulled and scheduled for execution. 

## I can't execute Spark job on Azure. 

The current default deployment procedure on Azure doesn't deploy HDFS/Spark. So Spark job execution is not available. 

## For 'az login', when I type in the device code, the web page prompt me again for the code. 

It seems that sometime the browser (Edge, Chrome) cache another identity not intended to be used with az login. To get around, please start the browser in (in-private) or (incognito) mode, you may then enter the 