#! /bin/bash
set -ex

function fail {
  echo $1 >&2
  exit 1
}

function retry {
  local n=1
  local max=3
  local delay=3
  while true; do
    "$@" && break || {
      if [[ $n -lt $max ]]; then
        ((n++))
        echo "Command failed. Attempt $n/$max:"
        sleep $delay;
      else
        fail "The command has failed after $n attempts."
      fi
    }
  done
}

function setup_sshd {
    # if "DLWS_HOST_NETWORK" enabled, randomly generate port in range: 40000-49999
    if [ "$DLWS_HOST_NETWORK" = "enable" ];
    then
        SSH_PORT=$DLWS_SD_SELF_SSH_PORT
        sed -i -E "s/^#?Port 22/Port ${SSH_PORT}/" /etc/ssh/sshd_config || exit 1
    else
        SSH_PORT=22
    fi
    #echo "AllowUsers ${DLWS_USER_NAME} root" | tee -a /etc/ssh/sshd_config > /dev/null
    #echo "AllowGroups dltsadmin" | tee -a /etc/ssh/sshd_config > /dev/null
    echo "${SSH_PORT}" > ${PROC_DIR}/SSH_PORT
    echo "${POD_IP}" > ${PROC_DIR}/POD_IP

    time /etc/init.d/ssh restart || exit 1
}

retry setup_sshd
