[![Build Status](https://travis-ci.org/microsoft/DLWorkspace.svg?branch=dltsdev)](https://travis-ci.org/microsoft/DLWorkspace?branch=dltsdev)
[![Coverage Status](https://coveralls.io/repos/github/microsoft/DLWorkspace/badge.svg?branch=dltsdev)](https://coveralls.io/github/microsoft/DLWorkspace?branch=dltsdev)

# [](#header-1)[Project Overview](docs/index.md)

Deep Learning Workspace (DLWorkspace) is an open source toolkit that allows AI scientists to spin up an AI cluster in turn-key fashion.
Once setup, the DLWorkspace provides web UI and/or restful API that allows AI scientist to run job (interactive exploration, training, inferencing, data analystics)
on the cluster with resource allocated by DL Workspace cluster for each job (e.g., a single node job with a couple of GPUs with GPU Direct connection, or a distributed job with multiple GPUs per node). DLWorkspace also provides
unified job template and operating environment that allows AI scientists to easily share their job and setting among themselves and with outside community. DLWorkspace out-of-box supports all major deep learning toolkits (PyTorch, TensorFlow, CNTK, Caffe, MxNet, etc..), and supports popular big data analytic toolkit such as hadoop/spark. 


# [](#header-3)Documentations

## [DLWorkspace Cluster Deployment](docs/deployment/Readme.md)

## [Frequently Asked Questions](docs/KnownIssues/Readme.md)
