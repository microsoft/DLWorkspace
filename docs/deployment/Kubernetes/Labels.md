# The Kubernete labeling of DL workspace nodes. 

DL workspace may run a number of services the cluster. Each service runs according to labels defined in "kubelabels" section in the configuration file, and can be modified in configuration file. 

1. Change of label behavior. 

   For example, we want service_a only run on node_ and node_b in the cluster, we can make the changes as follows:

   1. In config.yaml, specify:
   ```
   kubelabels:
       service_a : service_a_node_marker
   ```

   In the node section, you may then write
   ```
   node_a:
       service_a_node_marker : <<any_flag>>
   node_b:
       service_a_node_marker : <<any_flag>>
   ```

   service will run on node_a and node_b. 
   