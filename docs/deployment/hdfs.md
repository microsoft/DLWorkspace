# Deployment of HDFS on a kubernete cluster. 

The document describes the procedure to deploy HDFS across a cluster. 

1. Configure HDFS configuration section on the cluster. 
  You will need to specify: 1) the nodes, 2) block device used by HDFS. 
  
  ```
  hdfs:
    partitions: /dev/sd[c|d]1
  kubelabels:
    hdfs: worker or <<hdfs_labels>> # nodes marked with hdfs_labels will be used for HDFS. 
  ```

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
