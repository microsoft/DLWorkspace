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

sed 's/##etcd_endpoints##/'"$ETCD_ENDPOINTS"'/g' /etc/flannel/options.env > rendered.options.env
sudo cp rendered.options.env /etc/flannel/options.env

sed 's/$KUBE_API_SERVER/'"$KUBE_API_SERVER"'/g' /etc/kubernetes/worker-kubeconfig.yaml > rendered.worker-kubeconfig.yaml
sudo cp rendered.worker-kubeconfig.yaml /etc/kubernetes/worker-kubeconfig.yaml

python3 render_kube_service.py -t worker.kubelet.service.template -r worker.kubelet.service -nt $KUBE_LABELS
sed 's/$GPU_TYPE/'"$GPU_TYPE"'/g' worker.kubelet.service > rendered.worker.kubelet.service
sudo cp rendered.worker.kubelet.service /etc/systemd/system/kubelet.service

bash ./post-worker-deploy.sh
bash ./fileshare_install.sh
bash ./mnt_fs_svc.sh
