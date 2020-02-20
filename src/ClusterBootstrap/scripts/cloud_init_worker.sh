#!/bin/bash
# set -ex
bash ./prepare_vm_disk.sh
bash ./prepare_ubuntu.sh
bash ./disable_kernel_auto_updates.sh
bash ./docker_network_gc_setup.sh
bash ./dns.sh

bash ./pre-worker-deploy.sh
source ../boot.env
awk -F, '{print $1, $2}' worker.filemap | xargs -l ./mkdir_and_cp.sh

./render_env_vars.sh worker/kubelet/options.env.template /etc/flannel/options.env ETCD_ENDPOINTS
./render_env_vars.sh worker/kubelet/worker-kubeconfig.yaml.template /etc/kubernetes/worker-kubeconfig.yaml KUBE_API_SERVER
./render_env_vars.sh worker.kubelet.service.template /etc/systemd/system/kubelet.service KUBE_LABELS

bash ./post-worker-deploy.sh
bash ./fileshare_install.sh
bash ./mnt_fs_svc.sh
