# Deployment of GlusterFS on a kubernete cluster. 

The document describes the procedure to deploy glusterFS across a cluster. GlusterFS needs to access block device on the cluster. For manipulation of block device, please refer to [Partition.md](Partition.md). 

0. [Optional] Repartition(Repartition.md) some data drives on the cluster and use those partition for glusterFS. 
  The partition used is specified in configuration: glusterFS -> partitions

1. Format thin_pool volumes to be used by glusterFS. 
  ```
  deploy.py glusterfs create 
  ```
  Those pools can be removed via
  ```
  deploy.py glusterfs remove
  ```
  These two command may destroy all data stored on the target glusterFS partition, please use them with care. 
  
2. Configure and build glusterFS docker 
  ```
  deploy.py glusterfs config
  ```
  
3. Start glusterFS daemon set. 
  ```
  deploy.py kubernetes start glusterfs
  ```
  The glusterfs volume can now be used. 
  
4. [Optional] Stop glusterFS daemon set. 
  ```
  deploy.py kubernetes stop glusterfs
  ```