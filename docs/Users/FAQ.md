# Frequently Asked Question by DL Workspace Users

1. Can I run multiple jobs (training, inferencing, etc..) on the same GPU in DL Workspace? 

   Nvidia doesn’t really build a GPU like CPU for sharing. 
   See this [quora post](https://www.quora.com/Can-I-run-multiple-deep-learning-models-on-the-same-GPU), it is generally not recommended. 

   In a particular case (Caffe training), we found that with certain Nvidia GPU, when multiple Caffe sessions run on the same GPU, 
   **all** the Caffe sessions will be freeze and cannot even be killed. The Gpus will be occupied forever unless we restart the 
   physical machine, which will kill other jobs on the same node. We have observed that the problem occur on one Nvidia GPU card, not on
   another (of different model). Both machines are installed with Ubuntu OS, and we tried to run both job outside of container (to eliminate the 
   potential impact caused by DL Workspace). We believe that the issue is caused by Nvidia driver or Caffe. 

   Before GPU virtualization becomes mature, we recommend not to run multiple jobs on the same GPU. 

2. When I run iPython notebook as root credential, the job failed with message: 
   ```
    [C 00:16:52.684 NotebookApp] Running as root is not recommended. Use --allow-root to bypass.
   ```

   As the error message suggest, if you decide to run iPython with root credential, you will need to change the command to:

   ```
   export HOME=/job && jupyter notebook --no-browser --port=8888 --ip=0.0.0.0 --notebook-dir=/ --allow-root
   ```


