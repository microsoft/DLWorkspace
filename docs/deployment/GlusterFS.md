# Deployment of GlusterFS on a kubernete cluster. 

The document describes the procedure to deploy glusterFS across a cluster. GlusterFS needs to access block device on the cluster. For manipulation of block device, please refer to [Partition.md](Partition.md). 

1. Repartition(Repartition.md) some data drives on the cluster and use those partition for glusterFS. 
  The partition used is specified in configuration: 
  
  ```
  glusterFS:
    partitions: <<regular expression matching drives deploying glusterFS>>
  ```

  You may also specify nodes that glusterFS will be deployed via:
  ```
  kubelabels:
    glusterfs: worker or <<glusterfs_labels>>
  ```
  
  If you do not want to deploy glusterFS to all worker node, you could use "glusterfs_labels", and mark node to be deployed with glusterfs with the specific "glusterfs_labels". Please see [node labeling](Labels.md) for more information. 

2. Format thin_pool volumes to be used by glusterFS. 
  ```
  deploy.py glusterfs create 
  ```
  Those pools can be removed via
  ```
  deploy.py glusterfs remove
  ```
  These two command may destroy all data stored on the target glusterFS partition, please use them with care. You will be asked to confirm the command specifically. 
  
3. Configure and build glusterFS docker 
  ```
  deploy.py glusterfs config
  ```
  
4. Start glusterFS daemon set and mount volumes 
  ```
  deploy.py --glusterfs start kubernetes start glusterfs
  ```
  The second time around, glusterFS daemon set can be started with 
  ```
  deploy.py start kubernetes start glusterfs
  ```
  The glusterfs volume can now be used. 
  You may use:
  ```
  deploy.py --glusterfs format kubernetes start glusterfs
  ```
  to remove any wrongly created volume in glusterfs, and recreate the volume. Please caution that this command will erasure all data on the glusterfs volume. Please use with care. 
  
5. [Administrator] Stop glusterFS daemon set. 
  ```
  deploy.py kubernetes stop glusterfs
  ```

6. Trouble shooting:
   You may log onto a node deployed with glusterfs, and check its operating log at: /var/log/glusterfs.
   The launch log is available at /var/log/glusterfs/launch/launch.log
