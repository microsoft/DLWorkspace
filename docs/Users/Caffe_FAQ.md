# Frequently Asked Question for Caffe Users

1. I have failed to start multiple training jobs on Caffe using the same dataset. 

   You may use a data store (e.g., Lmdb), that is not thread safe. Either use a thread safe data store, or copy the data for each training job. 