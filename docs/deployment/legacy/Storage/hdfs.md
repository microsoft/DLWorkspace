# Deployment of HDFS on a kubernete cluster. 

The document describes the procedure to setup HDFS, either in high availability mode (multiple zookeepers and journal nodes, one active namenode and one standby namenode, multiple datanodes ), or with a single namenode across a cluster. 

1. Configure HDFS configuration section on the cluster. 
  You will need to specify: 1) the nodes, 2) block device used by HDFS and their mounting location. 
  
  ```
  hdfs:
    partitions: /dev/sd[c|d]1
    datadirs:
      /dev/sdc1:/mnt/sdc1
      /dev/sdc2:/mnt/sdc2

  kubelabels:
    hdfs: worker or <<hdfs_labels>> # nodes marked with hdfs_labels will be used for HDFS. 
  ```
  In default, if the cluster has more than 1 infrastructure node, HDFS will be deployed in high availability(HA) mode. If the cluster has just 1 infrastructure node, HDFS will be deployed with single name node. Zookeeper and journal nodes only need to be deployed in HA mode, and can be skipped with single name node mode. 

2. Format and partition device used by hdfs via:
  ```
  deploy.py hdfs create 
  ```
  This command may destroy all data on the target device, so you will be asked to manually confirm the operation. 

  If already formatted, you may just mount device by:
  ```
  deploy.py hdfs mount
  ```
  The device can be unmounted via:
  ```
  deploy.py hdfs umount
  ```

3. Configure zookeeper and HDFS
  ```
  deploy.py docker push zookeeper
  deploy.py hdfs config
  ```

4. [High Available Cluster]Deploy HDFS zookeeper and journal node
  ```
  deploy.py kubernetes start zookeeper
  deploy.py kubernetes start hdfsjournal
  ```
  You may shutdown zookeeper and journal node via:
  ```
  deploy.py kubernetes stop hdfsjournal
  deploy.py kubernetes stop zookeeper
  ```

5. Format HDFS namenode/zookeeper
  Please wait for zookeeper and hdfsjournal pods to be launched, and then do:
  ```
  deploy.py kubernetes start hdfsformat
  [High Available Cluster] deploy.py kubernetes start hdfsstandby
  deploy.py kubernetes stop hdfsformat
  [High Available Cluster] deploy.py kubernetes stop hdfsstandby
  ```
  Command 
  ```
  deploy.py --force kubernetes start hdfsformat
  ```
  will wipe out namenode information, and restart the cluster. 


6. Deploy HDFS namenodes
  ```
  deploy.py kubernetes start hdfsnamenode
  ```
7. Deploy HDFS datanodes
  ```
  deploy.py kubernetes start hdfsdatanode
  ```
8. Mount HDFS volume
  ```
  deploy.py mount
  ```
