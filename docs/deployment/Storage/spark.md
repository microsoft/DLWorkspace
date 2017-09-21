# Running spark job on a kubernete cluster. 

The document describes the procedure to setup a spark job on a DL Workspace cluster. 

1. Launch Yarn resource manager and node manager
  ```
  deploy.py kubernetes start yarnresourcemanager
  deploy.py kubernetes start yarnnodemanager
  ```
  You may disable yarn resource manager and node manager by running:
  ```
  deploy.py kubernetes stop yarnresourcemanager
  deploy.py kubernetes stop yarnnodemanager
  ```

2. Build spark container
  ```
  deploy.py hdfs config
  ```

3. Launch Spark container. Use SSH template, you can launch a spark job via DL Workspace Web Portal. Once SSH into the container, you can use the follows to luanch a spark job: 
  ```
  cd /usr/local/spark
  env YARN_CONF_DIR=/usr/local/hadoop/etc/hadoop ./bin/spark-submit --class org.apache.spark.examples.SparkPi --master yarn --deploy-mode cluster --driver-memory 4g --executor-memory 2g --executor-cores 1 --queue thequeue examples/jars/spark-examples*.jar 10
  ```
