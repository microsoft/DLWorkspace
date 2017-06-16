# Problem Description 
in some particular case, caffe (potentially other toolkit) leaves zombie processes in the job container. The docker container cannot be stopped then. 
The zombie processes also hold GPU memory. 

There is currently no solution to kill these containers but reboot the system. 

```
docker top a7600d30f339
UID                 PID                 PPID                C                   STIME               TTY                 TIME                CMD
5268799+            2576                31109               99                  Jun07               ?                   5-00:52:38          [caffe] <defunct>
5268799+            23792               31109               99                  Jun07               ?                   4-20:04:31          [caffe]
```

```
ps -axl | grep 2576
0 526879956 2576 31109 20 0      0     0 -      Zl   ?        7253:09 [caffe] <defunct>
```

```
+-------------------------------+----------------------+----------------------+
|   4  Tesla M40 24GB      Off  | 0000:83:00.0     Off |                    0 |
| N/A   38C    P8    17W / 250W |   1388MiB / 22939MiB |      0%      Default |
+-------------------------------+----------------------+----------------------+
|   5  Tesla M40 24GB      Off  | 0000:89:00.0     Off |                    0 |
| N/A   34C    P0    67W / 250W |   1388MiB / 22939MiB |    100%      Default |
+-------------------------------+----------------------+----------------------+

```

# System Environment
  1. baseos: coreOS Linux 10.196.41.89 4.7.3-coreos-r2 #1 SMP Thu Feb 2 02:26:10 UTC 2017 x86_64 Intel(R) Xeon(R) CPU E5-2690 v4 @ 2.60GHz GenuineIntel GNU/Linux
  2. GPU: 8 * Tesla M40 24GB
  3. Nvidia Driver version: 367.55, Cuda version: 8.0
  3. container OS: ubuntu
  
# Reproduce this issue:
  1. launch a multi-gpu caffe training job
  ```
  caffe train -gpu 0,1,2,3 --solver [solver.prototxt]
  ```

  2. launch another caffe training job using the same set of gpus
  ```
  caffe train -gpu 0,1,2,3 --solver [solver.prototxt]
  ```
  
  3. the two jobs cannot be stopped peacefully. If kill -9 is used, the two jobs will become zombie process and still hold the GPU memory. 
  Even worse, the docker container cannot be kill either due to the zombie process. 
