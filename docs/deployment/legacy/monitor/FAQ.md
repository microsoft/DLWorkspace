# Frequently Asked Question on Cluster monitoring

1. What is the mechanism in monitoring the operation of the cluster. 
 
   By default, we have installed kubernete dash board and grafana to monitor the status of the cluster and individual node. 

2. How to access Kubernete dashboard/Grafana. 

   1. Kubernete Dashboard can be accessed at: https://[infranode]/ui (notice https)
      Grafana can be accessed at: https://[infranode]/api/v1/proxy/namespaces/kube-system/services/monitoring-grafana/?orgId=1

   2. When visiting the monitoring site, you may get a message on certificate error. 
      1. For Chrome, the error message will be like "Your connection is not private. Attackers might be trying to steal your information from [infranode] (for example, passwords, messages, or credit cards). "
         1. Please click "Advanced"
         2. Click, "Proceed to [infranode](unsafe)"
      2. For Microsoft Edge, you will get a message "This site is not secure". 
         1. Please click "Details"
         2. Click, "Go on to the web page(Not recommended)"

    3. You will need the admin username and password for the interface. They are set/automatically generated during the deployment procedure. Please look for the file cluster.yaml or config.yaml or azure_cluster_config.yaml in src/ClusterBootstrap, look at the linke basic_auth:

    ```
    basic_auth: [admin_password], [admin_username]
    ```
    Type in the admin_username and admin_password to access Kubernete Dashboard and Grafana. 

3. How to access HDFS/Yarn dashboard. 
   You can access HDFS dashboard at http://[infrastructurenode]:50070/. YARN dashboard can be accessed at http://[infrastructurenode]:8088/

       
