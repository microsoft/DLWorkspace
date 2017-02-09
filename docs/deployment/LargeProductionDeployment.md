# Large Production Deployment

Large production deployment aims for a large cluster with stability deployment. In such deployment, there will be K ETCD/master servers form a cluster group. 
In addition, there will be N worker node. The ETCD server will not be scheduled of works. This is because in Kubernetes, docker service requires flannel, which in turns require Etcd. Scheduling additional work on ETCD undermine its stability. 

