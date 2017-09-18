# [](#header-1)Project Overview

Deep Learning Workspace (DLWorkspace) is an open source toolkit that allows AI scientists to spin up an AI cluster in turn-key fashion (either in a public cloud such as Azure, or in an on-perm cluster). It has been used in daily production for Microsoft internal groups (e.g., Microsoft Cognitive Service, SwiftKey, Bing Relevance, etc.. ).
Once setup, the DLWorkspace provides web UI and/or restful API that allows AI scientist to run job (interactive exploration, training, inferencing, data analystics)
on the cluster with resource allocated by DL Workspace cluster for each job (e.g., a single node job with a couple of GPUs with GPU Direct connection, or a distributed job with multiple GPUs per node). DLWorkspace also provides
unified job template and operating environment that allows AI scientists to easily share their job and setting among themselves and with outside community. DLWorkspace out-of-box supports all major deep learning toolkits (TensorFlow,CNTK, Caffe, MxNet, etc..), and supports popular big data analytic toolkit such as hadoop/spark. 

# [](#header-2)Tutorials

Here is a few short video clips that can quickly explain DLWorkspace. Note the PPT link will only work in github.com repo, not in github.com pages. 

* [DL Workspace: CNTK](https://youtu.be/3O0uwUwPRho) [(PPT)](Presentation/Video/Running_CNTK.pptx)
* [DL Workspace: TensorFlow](https://youtu.be/Xa7exVurUmE) [(PPT)](Presentation/Video/Running TensorFlow.pptx)
* [DL Workspace: Spark](https://youtu.be/9kV9_w-eQYY) [(PPT)](Presentation/Video/Running Spark.pptx)
* [Installation-Azure](https://youtu.be/inDcl85-TRw) [(PPT)](Presentation/Video/Installation-Azure.pptx)
* [Installation-On-Prem](https://youtu.be/nKLmt8Ace50) [(PPT)](Presentation/Video/Installation-On-Prem.pptx)

# [](#header-3)Documentations

## [DLWorkspace Cluster Deployment](deployment/Readme.md)

* [Azure Cluster](deployment/Azure/Readme.md)
* [On prem, Ubuntu Cluster](deployment/Ubuntu.md)

## Known Issues

* [Deployment Issue](deployment/Deployment_Issue.md)
* Container Issue: [Zombie Process](KnownIssues/zombie_process.md)

## Presentation

* [Overview](Presentation/1707/DL_Workspace_Overall.pptx)
* [Job scheduling](Presentation/1707/job_scheduling_runtime.pptx)
* [Kubernetes modification](Presentation/1707/Kubernetes_Modifications.pptx)
* [Shared file system](Presentation/1707/DL_Workspace_Cluster_Deployment_GlusterFS.pptx)
* [Interactive jobs](Presentation/1707/interactive_job.pptx)
* [Engineering practices](Presentation/1707/DL_Workspace_Engineering_Practices.pptx)








