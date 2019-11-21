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
    time apt-get update && time apt-get install -y openssh-server

    # if "DLWS_HOST_NETWORK" enabled, randomly generate port in range: 40000-49999
    if [ "$DLWS_HOST_NETWORK" = "enable" ];
    then
        SSH_PORT=$(( $RANDOM % 10000 + 40000 ))
        sed -i -E "s/^#?Port 22/Port ${SSH_PORT}/" /etc/ssh/sshd_config || exit 1
    else
        SSH_PORT=22
    fi
    echo "${SSH_PORT}" > ${PROC_DIR}/SSH_PORT
    echo "${POD_IP}" > ${PROC_DIR}/POD_IP

    time service ssh restart || exit 1
}

retry setup_sshd
