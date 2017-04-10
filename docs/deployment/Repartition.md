# Repartition 

You may use 'deploy.py' to manage the partition of the data drives in the cluster. 

0. You may specify the data-disk on the clsuter node by modifying the configuration parameter, the information is specified via regular expression. 
   ```
   data-disk: /dev/[sh]d[^a]
   ```

1. Show all data partitions:
   ```
   deploy.py partition ls
   ```
   
2. Repartition all drives:
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