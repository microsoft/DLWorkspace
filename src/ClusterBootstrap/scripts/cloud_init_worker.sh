#!/bin/bash
# set -ex
bash ./prepare_vm_disk.sh
bash ./prepare_ubuntu.sh
bash ./disable_kernel_auto_updates.sh
bash ./docker_network_gc_setup.sh
bash ./dns.sh
bash ./pre-worker-deploy.sh
awk -F, '{print $1, $2}' filemap | xargs -l ./mkdir_and_cp.sh
bash ./post-worker-deploy.sh
bash ./fileshare_install.sh
bash ./mnt_fs_svc.sh
