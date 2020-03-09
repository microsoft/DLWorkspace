# Frequently asked questions (FAQ) on HDFS. 

* When I visit a HDFS volume, I got the error "Transport endpoint is not connected". 

  We fuse mount HDFS share at the host, and map the share into the container. Currently, it seems that the HDFS share can only be accessed via super user (root) credential. If you would like to use HDFS share in file system fashion, please change into super user credential, 
  ```
    sudo su
  ```
  and then use the HDFS share in the container. 

  Please note 
  * Visit the HDFS share in container with credential other than super user not only disconnect the HDFS share in this container, but all other containers on the host.
  * Even if the host HDFS share recovers, the container HDFS share will stay disconnected. You have to launch a different container for access. 
  * If you are unsatisfied with the above behavior, please mount the HDFS file share directly in container, you can use install hdfs fuse mount on Ubuntu via:
    ```
    wget http://archive.cloudera.com/cdh5/one-click-install/trusty/amd64/cdh5-repository_1.0_all.deb; 
	sudo dpkg -i cdh5-repository_1.0_all.deb; 
	sudo rm cdh5-repository_1.0_all.deb; 
	sudo apt-get update; 
	sudo apt-get --no-install-recommends install -y default-jre; 
	sudo apt-get --no-install-recommends install -y --allow-unauthenticated hadoop-hdfs-fuse;
    ```
    Then, you can mount HDFS share via:
    ```
    hadoop-fuse-dfs hdfs://<namenode_server_name> <mount_point>
    ```
    

