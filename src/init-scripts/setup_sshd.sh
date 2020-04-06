#!/bin/bash
set -ex

function fail {
  echo $1 >&2
  exit 206
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
    SSH_PORT=$DLTS_SD_SELF_SSH_PORT
    sed -i -E "s/^#?Port 22/Port ${SSH_PORT}/" /usr/etc/sshd_config || exit 207

    echo "${SSH_PORT}" > ${PROC_DIR}/SSH_PORT
    echo "${POD_IP}" > ${PROC_DIR}/POD_IP

    time /etc/init.d/ssh restart || exit 208
}

retry setup_sshd
