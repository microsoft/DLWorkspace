#!/bin/bash
set -ex

CWD=$(dirname $0)

hostname
whoami

. /dlts-runtime/env/init.env
sh -x /dlts-runtime/install.sh

echo bootstrap starts at `date`

# https://stackoverflow.com/a/26759734/845762
if ! [ -x "$(command -v sudo)" ] ; then
    time apt-get update && time apt-get --no-install-recommends install -y sudo
fi

# Reorder GPU with NVLink (Allow failure) for jobs requesting more than 1 GPU
set +e
if [[ -x "$(command -v nvidia-smi)" ]] && [[ "${DLTS_NUM_GPU_PER_WORKER}" -gt 1 ]]; then
    GPU_TOPO=/dlts-runtime/gpu_topo
    TOPO_FILE=/tmp/topo
    CWD=$(dirname $0)
    nvidia-smi topo -p2p n | head -n $((${DLTS_NUM_GPU_PER_WORKER} + 1)) | tail -n ${DLTS_NUM_GPU_PER_WORKER} | awk '{$1=""; print $0}' | sed 's/ //' | tee ${TOPO_FILE}
    export CUDA_VISIBLE_DEVICES=$(${GPU_TOPO} ${TOPO_FILE} | sed 's/ //g')
fi
set -e

bash ${CWD}/init_user.sh
bash ${CWD}/setup_ssh_config.sh

echo bootstrap ends at `date`

mkdir -p /dlts-runtime/status
touch /dlts-runtime/status/READY

set +e
# Execute user's command for the job
if [ "$DLTS_ROLE_NAME" = "worker" ];
then
    exec /usr/local/bin/init runuser -l ${DLTS_USER_NAME} -c "sleep infinity"
else
    printenv DLTS_LAUNCH_CMD > /dlts-runtime/status/job_command.sh
    chmod +x /dlts-runtime/status/job_command.sh
    exec /usr/local/bin/init runuser -s /bin/bash -l ${DLTS_USER_NAME} -c /dlts-runtime/status/job_command.sh
fi
