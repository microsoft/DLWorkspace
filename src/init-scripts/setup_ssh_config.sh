#! /bin/bash
set -ex

JOB_DIR='/job'


if [ "$DLWS_ROLE_NAME" = "ps" ];
then
    # wait until all workers are ready
    all_workers_ready=false
    while [ "$all_workers_ready" != true ]
    do
        # update it to false if any worker is not ready
        all_workers_ready=true

        for i in $(seq 0 $(( ${DLWS_NUM_WORKER} - 1 )))
        do
            worker="worker-${i}"
            file="${JOB_DIR}/${worker}/running/ROLE_READY"
            #echo $file

            if [ ! -f $file ]; then
            echo "${worker} not ready!"
            all_workers_ready=false
            sleep 10
            fi
        done
    done
fi

# generate ps host list
ps_host_list=""
for i in $(seq 0 $(( ${DLWS_NUM_PS} - 1 )) )
do
    ps_host_list+="ps-${i} "
done

# generate worker host list
worker_host_list=""
if [ "$DLWS_ROLE_NAME" = "master" ];
then
    worker_host_list="${DLWS_ROLE_NAME}"
else
    for i in $(seq 0 $(( ${DLWS_NUM_WORKER} - 1 )) )
    do
        worker_host_list+="worker-${i} "
    done
fi

# generate host list
host_list="${ps_host_list} ${worker_host_list}"

# generate ~/ssh_config
SSH_CONFIG_FILE="/job/ssh_config"
>${SSH_CONFIG_FILE}
chown ${DLWS_USER_NAME} ${SSH_CONFIG_FILE}

for host in ${host_list}
do
    role_dir=${JOB_DIR}/${host}
    port=$(cat "${role_dir}/running/SSH_PORT")
    ip=$(cat "${role_dir}/running/POD_IP")
    cat >>${SSH_CONFIG_FILE} <<EOF

Host ${host}
  HostName ${ip}
  Port ${port}
  User ${DLWS_USER_NAME}
  StrictHostKeyChecking no
  UserKnownHostsFile /dev/null

EOF
done

# copy ssh config to ~/.ssh/config
cp ${SSH_CONFIG_FILE} /home/${DLWS_USER_NAME}/.ssh/config && chown ${DLWS_USER_NAME} /home/${DLWS_USER_NAME}/.ssh/config && chmod 600 /home/${DLWS_USER_NAME}/.ssh/config
mkdir -p /root/.ssh && cp /home/${DLWS_USER_NAME}/.ssh/* /root/.ssh/ && chown root /root/.ssh/* && chmod 600 /root/.ssh/*
for role_dir in ${JOB_DIR}/*/ # list directories in the form "/JOB_DIR/role/"
do
    role_dir=${role_dir%*/} # remove the trailing "/"
    if [[ ${role_dir} == *logs ]];
    then
        continue
    fi
    role=$(basename ${role_dir})
    echo "Setup ssh config for ${role}"
    ssh ${role} "cp ${SSH_CONFIG_FILE} /home/${DLWS_USER_NAME}/.ssh/config && chown ${DLWS_USER_NAME} /home/${DLWS_USER_NAME}/.ssh/config && chmod 600 /home/${DLWS_USER_NAME}/.ssh/config"
done

# generate /job/hostfile
SLOT_FILE="/job/hostfile"
>${SLOT_FILE}
chown ${DLWS_USER_NAME} ${SLOT_FILE}

for host in ${worker_host_list}
do
    slots=${DLWS_NUM_GPU_PER_WORKER}
    cat >>${SLOT_FILE} <<EOF
${host} slots=${slots}
EOF
done
