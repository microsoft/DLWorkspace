# Partition disks in DL Workspace

DL Workspace provides some scripts tool for you to partition the data-disk on the clusters. However, you can use your own favorite management tools for the task. Alternatively, you can use the [distributed script tool](../Scripts/Readme.md) provided by DL Workspace. 

1. In config.yaml, please specify the data-disk on the cluster node as follows. The information is specified via [python regular expression](https://docs.python.org/2/library/re.html). 
   ```
   data-disk: /dev/[sh]d[^a]
   ```

2. You can list all data partitions in the cluster as:
   ```
   deploy.py partition ls
   ```
   
3. You can repartition all drives:
   ```
   deploy.py partition create [args]
   ```
   As repartition destroyes all data on existing drives, the program will ask you to reconfirm the operation. The default is repartition the entire drive to one disk. 
   ```
   deploy.py partition create n
   ```
   will partition each data disk on the node to n equal partitions. 
   ```
   deploy.py partition create s_1, s_2, ..., s_n 
   ```
   will create n partitions. If s_i < 0, the partition will be of size s_i GB, if s_i > 0, the partition will be created roughly proportional to the value of s_i. Internally, we use 'parted --align optimal start% end%' to create data partitions, so the size of the partition will be rounded to 1% of the size of the disk. 