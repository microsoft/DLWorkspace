# Running spark job on a kubernete cluster. 

The document describes the procedure to run a spark job on a DL Workspace cluster. Please note that the procedure below will be significantly updated in a future release to stream line the process. 

1. Build Spark docker
  ```
  deploy.py docker push spark
  ```

2. Launch Spark container
  ```
  deploy.py kubernetes start spark
  ```

3. Ssh into spark container, go to spark directory
  ```
  deploy.py kubectl exec -ti spark-pod
  cd /usr/local/spark/bin
  ```

4. You should be able to execute spark command, e.g., 
  ```
  run-example SparkPi
  ```
