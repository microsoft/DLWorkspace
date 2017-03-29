# Deployment of GlusterFS on a kubernete cluster. 

The document describes the procedure to deploy glusterFS across a cluster. GlusterFS needs to access block device on the cluster. For manipulation of block device, please refer to [Partition.md](Partition.md). 

0. [Optional] Repartition(Repartition.md) some data drives on the cluster to use glusterFS. 

1. [Optional] Install python on all nodes. (python is used by GlusterFS deployment and virtual volume management )
  ```
  deploy.py --sudo runscriptonall script/install-python-on-coreos.sh
  ```
  You may verify python installation by:
  ```
  deploy.py execonall /opt/bin/python --version
  ```
  

2. When start a glusterFS cluster, please use command:
  ```
  deploy.py glusterFS start [param]
  ```
  The parameter can be a number, which simply translates into /dev/[s|h]d[^a][number], and will install the glusterFS on all #number partition of disk other than the system disk (/dev/sda or /dev/hda). 