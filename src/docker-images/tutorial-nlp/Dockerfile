#First build Tutorial tensorflow
FROM dlws/tutorial-horovod:1.6
MAINTAINER Jin Li <jinlmsft@hotmail.com>

# Add Glove vectors 
RUN mkdir -p /utils/glove; cd /utils/glove; \
    wget http://nlp.stanford.edu/data/glove.6B.zip; \ 
    unzip glove.6B.zip; \
    rm glove.6B.zip glove.6B.?00d.txt 
# Add Yolo models
RUN cd /utils; git clone --recurse-submodules git://github.com/DLWorkspace/YAD2K
RUN mkdir /utils/models; cd /utils/models; wget https://dlwsdata.blob.core.windows.net/models/yolo.h5
# Additional utility
RUN pip3 install music21 emoji faker Babel pydub dill
RUN cd /utils; git clone --recurse-submodules https://github.com/DLWorkspace/nmt
RUN mkdir /utils; cd /utils;  git clone --recurse-submodules git://github.com/DLWorkspace/deep-learning-coursera

# The following install Cython & Pycocotools 
RUN pip3 install Cython
RUN cd /utils && \
    git clone https://github.com/pdollar/coco.git && \
    cd /utils/coco/PythonAPI && \
    make && \
    make install && \
    python3 setup.py install 

# Install mask RCNN
RUN cd /utils && git clone https://github.com/matterport/Mask_RCNN

# Install allennlp
RUN pip3 install allennlp 

# The following operation needs GPU to create yolo.h5, This currently only works for Yolo V2 (V1 and V3 have layers that can't be interpreted)
# RUN cd /utils/YAD2K; \
#    wget https://pjreddie.com/media/files/yolov2.weights; \
#    wget https://raw.githubusercontent.com/pjreddie/darknet/master/cfg/yolov2.cfg; \
#    ./yad2k.py yolov2.cfg yolov2.weights model_data/yolo.h5
