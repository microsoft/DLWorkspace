# Configure DL workspace cluster

This document describes the procedure to write a configuration file for your DL workspace cluster. 

Please copy the configuration template at /src/DLworkspace/config.yaml.template to /src/DLworkspace/config.yaml. Then, please edit the config.yaml file and provide the following information:

1. {{cluster_name}}: replace it with the your DL workspace cluster name, e.g., ccs1

2. {{etcd_node_num}}: replace it with the number of Etcd servers. For a production cluster, this should be at least 3 for reliability. It is OK to use 1 for a test cluster. Please note that if you select to use N etcd servers, you should setup exactly that number of etcd server during deployment. 

3. {{apiserver_password,apiserver_username,apiserver_group}}: replace it with a password, a username and the group of API server. If you use "helloworld,adam,apig", then the API server can be administered through username adam, and password helloworld. Please do **__not__** put space in the string, as the space will be taken as part of the username/password.  

