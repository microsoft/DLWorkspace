#/bin/bash
set -ex

export ENV_FILE=/pod.env

# install required pkgs
export DEBIAN_FRONTEND=noninteractive

# setup user and group, fix permissions
addgroup --force-badname --gid  ${DLTS_GID} domainusers
adduser --force-badname --home /home/${DLTS_USER_NAME} --shell /bin/bash --uid ${DLTS_UID}  -gecos '' --gid ${DLTS_GID} --disabled-password ${DLTS_USER_NAME}
usermod -p $(echo ${DLTS_JOB_TOKEN} | openssl passwd -1 -stdin) ${DLTS_USER_NAME}
chown ${DLTS_USER_NAME} /home/${DLTS_USER_NAME}/ /home/${DLTS_USER_NAME}/.profile /home/${DLTS_USER_NAME}/.ssh || /bin/true
chmod 700 /home/${DLTS_USER_NAME}/.ssh || /bin/true

# setup sudoers
adduser $DLTS_USER_NAME sudo
echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

# export envs
# options '-e' for exported ENVs only
compgen -e | while read line; do
        if [[ $line != HOME* ]] && [[ $line != INTERACTIVE* ]] && [[ $line != LS_COLORS* ]]  && [[ $line != PATH* ]] && [[ $line != PWD* ]]; then
            # Since bash >= 4.4 we could use
            # echo "export ${line}=${!line@Q}" >> "${ENV_FILE}" ;
            # For compatible with bash < 4.4
            printf "export ${line}=%q\n" "${!line}" >> "${ENV_FILE}" ;
        fi; done
echo "export PATH=$PATH:\${PATH}" >> "${ENV_FILE}"
echo "export LD_LIBRARY_PATH=/usr/local/nvidia/lib64/:\${LD_LIBRARY_PATH}" >> "${ENV_FILE}"
# source the envs
grep -qx "^\s*. ${ENV_FILE}" /home/${DLTS_USER_NAME}/.profile || cat << SCRIPT >> "/home/${DLTS_USER_NAME}/.profile"
if [ -f ${ENV_FILE} ]; then
    . ${ENV_FILE}
fi
SCRIPT
