#/bin/bash
set -ex

#export POD_NAME=0511068a-7744-47af-b42f-bd3695
#export DLWS_GID=234324
#export DLWS_UID=234324
#export DLWS_USER=hayua
export DLWS_DIR=/dlws

# setup user and group, fix permissions
addgroup --force-badname --gid  ${DLWS_GID} domainusers
adduser --force-badname --home /home/${DLWS_USER} --shell /bin/bash --uid ${DLWS_UID}  -gecos '' --gid ${DLWS_GID} --disabled-password ${DLWS_USER}
usermod -p $(echo tryme2017 | openssl passwd -1 -stdin) ${DLWS_USER}
chown -R ${DLWS_USER} /home/${DLWS_USER}/ || /bin/true

# setup sudoers
adduser $DLWS_USER sudo
echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

# export envs
env | while read line; do
        if [[ $line != HOME=* ]] && [[ $line != INTERACTIVE* ]] && [[ $line != LS_COLORS* ]]  && [[ $line != PATH* ]]; then
            echo "export $line" >> ${DLWS_DIR}/${POD_NAME}.env ;
        fi; done
echo "export PATH=$PATH:\${PATH}" >> ${DLWS_DIR}/${POD_NAME}.env
echo "export LD_LIBRARY_PATH=/usr/local/nvidia/lib64/:\${LD_LIBRARY_PATH}" >> ${DLWS_DIR}/${POD_NAME}.env
# source the envs
echo "source ${DLWS_DIR}/${POD_NAME}.env" >> /home/${DLWS_USER}/.profile

# any command should run as ${DLWS_USER}
#runuser -l ${DLWS_USER} -c your_commands
