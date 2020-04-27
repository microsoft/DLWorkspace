#! /bin/bash
set -x

CWD=$(dirname $0)

# generate ps host list
ps_host_list=""
for i in $(seq 0 $(( ${DLTS_NUM_PS} - 1 )) )
do
    ps_host_list+="ps-${i} "
done

# generate worker host list
worker_host_list=""
if [ "$DLTS_ROLE_NAME" = "master" ];
then
    worker_host_list="${DLTS_ROLE_NAME}"
    self_name="${DLTS_ROLE_NAME}" # for testing self connection
else
    for i in $(seq 0 $(( ${DLTS_NUM_WORKER} - 1 )) )
    do
        worker_host_list+="worker-${i} "
    done
    self_name="${DLTS_ROLE_NAME}-${DLTS_ROLE_IDX}" # for testing self connection
fi

# generate host list
host_list="${ps_host_list} ${worker_host_list}"

# generate ~/.ssh/config
SSH_CONFIG_FILE=/home/${DLTS_USER_NAME}/.ssh/config
>${SSH_CONFIG_FILE}
chown ${DLTS_USER_NAME} ${SSH_CONFIG_FILE}
chmod 600 ${SSH_CONFIG_FILE}

for host in ${host_list}
do
    if [ "$DLTS_ROLE_NAME" = "master" ];
    then
        ip=$DLTS_SD_SELF_IP
        port=$DLTS_SD_SELF_SSH_PORT
    else
        role=${host%%-*}
        idx=${host##*-}

        ip_key=DLTS_SD_${role}${idx}_IP
        port_key=DLTS_SD_${role}${idx}_SSH_PORT
        ip=$(printenv $ip_key)
        port=$(printenv $port_key)
    fi
    cat >>${SSH_CONFIG_FILE} <<EOF

Host ${host}
  HostName ${ip}
  Port ${port}
  User ${DLTS_USER_NAME}
  StrictHostKeyChecking no
  UserKnownHostsFile /dev/null

EOF
    # also add entry to /etc/hosts
    echo -e "${ip}\t${host}" >> /etc/hosts
done

set +x

envs=(
LD_LIBRARY_PATH
LIBRARY_PATH
PATH
PYTHONPATH
NCCL_IB_DISABLE
NCCL_SOCKET_IFNAME
NCCL_VERSION
CUDA_VISIBLE_DEVICES
DLWS_HOST_NETWORK
DLTS_HOST_NETWORK
DLWS_JOB_ID
DLTS_JOB_ID
DLTS_JOB_TOKEN
DLWS_NUM_PS
DLTS_NUM_PS
DLWS_NUM_WORKER
DLTS_NUM_WORKER
DLWS_NUM_GPU_PER_WORKER
DLTS_NUM_GPU_PER_WORKER
DLWS_VC_NAME
DLTS_VC_NAME
DLWS_UID
DLTS_UID
DLWS_GID
DLTS_GID
DLWS_USER_NAME
DLTS_USER_NAME
DLWS_USER_EMAIL
DLTS_USER_EMAIL
DLWS_ROLE_NAME
DLTS_ROLE_NAME
DLWS_ROLE_IDX
DLTS_ROLE_IDX
)

SSH_ENVIRONMENT_FILE=/home/${DLTS_USER_NAME}/.ssh/environment

for env_key in "${envs[@]}" ; do
    if [ "`printenv $env_key`" != "" ] ; then
        printf $env_key >> $SSH_ENVIRONMENT_FILE
        printf = >> $SSH_ENVIRONMENT_FILE
        printenv $env_key >> $SSH_ENVIRONMENT_FILE
    fi
done
chown ${DLWS_USER_NAME} ${SSH_ENVIRONMENT_FILE}
chmod 600 ${SSH_ENVIRONMENT_FILE}

mkdir -p /root/.ssh && cp /home/${DLWS_USER_NAME}/.ssh/* /root/.ssh/ && chown root /root/.ssh/* && chmod 600 /root/.ssh/*

AUTHORIZED_FILE=/home/${DLTS_USER_NAME}/.ssh/authorized_keys
for env_key in `env | grep DLTS_PUBLIC_SSH_KEY_| cut -d = -f 1` ; do
    printenv $env_key >> $AUTHORIZED_FILE
done

PRIVATE_KEY_FILE=/home/${DLTS_USER_NAME}/.ssh/id_rsa
printenv DLTS_SSH_PRIVATE_KEY > $PRIVATE_KEY_FILE
chown ${DLTS_USER_NAME} ${SSH_ENVIRONMENT_FILE} ${AUTHORIZED_FILE} ${PRIVATE_KEY_FILE}
chmod 600 ${SSH_ENVIRONMENT_FILE} ${AUTHORIZED_FILE} ${PRIVATE_KEY_FILE}

set -x

mkdir -p /root/.ssh && cp /home/${DLTS_USER_NAME}/.ssh/* /root/.ssh/ && chown root /root/.ssh/* && chmod 600 /root/.ssh/*

# generate /job/hostfile
if [ "$DLTS_ROLE_NAME" = "master" ] || [ "$DLTS_ROLE_NAME" = "ps" ];
then
    SLOT_FILE="/job/hostfile"
    >${SLOT_FILE}
    chown ${DLTS_USER_NAME} ${SLOT_FILE}

    for host in ${worker_host_list}
    do
        slots=${DLTS_NUM_GPU_PER_WORKER}
        cat >>${SLOT_FILE} <<EOF
${host} slots=${slots}
EOF
    done
fi

bash ${CWD}/setup_sshd.sh

# make sure worker have sshd up and running
if [ "$DLTS_ROLE_NAME" = "ps" ];
then
    for host in ${host_list}
    do
        succ=false
        for i in `seq 1 3600` ; do
            echo `date` "testing $host"
            ssh $host "echo 1"
            # do not add code here
            rtn=$?
            echo `date` "done testing $host"
            if [ "$rtn" -eq "0" ] ; then
                succ=true
                echo "$host has done sshd setup"
                break
            else
                echo `date` "$host has not done sshd setup wait 1s"
                sleep 1
            fi
        done
        if [ "$succ" = "false" ] ; then
            echo `date` "could not establish ssh connection to $host, abort"
            exit 205
        fi
    done
else
    echo `date` "testing self"
    ssh ${self_name}
    # do not add code here
    rtn=$?
    echo `date` "done testing self"
    if [ "$rtn" -eq "0" ] ; then
        exit 0
    else
        echo "failed to test self"
        exit 209
    fi
fi
