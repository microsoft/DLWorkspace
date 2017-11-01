# A docker related to image operation. 

Here are the operations that you can do with this docker. 

* Image Classification (using Inception v3):
  ```
  cd /root/models/tutorials/image/imagenet
  python3 classify_image.py
  ```

* Image Retraining
  ```
  cd /tensorflow
  curl -L "https://storage.googleapis.com/download.tensorflow.org/models/inception_v3_2016_08_28_frozen.pb.tar.gz" |
    sudo tar -C tensorflow/examples/label_image/data -xz
  cd /tensorflow/tensorflow/examples/image_retraining
  ```

