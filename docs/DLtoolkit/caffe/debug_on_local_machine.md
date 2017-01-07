# How to debug on your local machine

```
nvidia-docker run -v /dlws-data/scratch/hongzl:/work -v /dlws-data/storage/imagenet:/data -ti caffe:gpu bash

caffe train --solver /work/caffe/solver_resnet18.prototxt
```
