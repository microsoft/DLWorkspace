#!/bin/bash

# These commands involve a lot of file system operations (cp, rm, etc.).
# File system operations are extremely slow in Centos cloud init - a few to tens
# of seconds for each operation. Defer these commands to lustre_mdt_or_oss.sh
# TODO: Look into the root cause to the slowness
#-----------------------------------------------------------------------------
#bash ./prepare_lustre_centos.sh
#bash ./dns.sh
#
#bash ./pre-worker-deploy.sh
#source ../boot.env
#./cloud_init_mkdir_and_cp.py -p file_map.yaml -u $USER -m $MOD_2_CP
#
#./render_env_vars.sh kubelet_worker/deploy/kubelet/options.env.template /etc/flannel/options.env ETCD_ENDPOINTS
#./render_env_vars.sh kubelet_worker/deploy/kubelet/worker-kubeconfig.yaml.template /etc/kubernetes/worker-kubeconfig.yaml KUBE_API_SERVER
#./render_env_vars.sh lustre.kubelet.service.template /etc/systemd/system/kubelet.service KUBE_LABELS
#
#bash ./post-worker-deploy.sh
#-----------------------------------------------------------------------------

bash ./setup_lustre.sh

