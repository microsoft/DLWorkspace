#!/bin/bash
set -ex

CWD=$(dirname $0)

. /dlts-runtime/env/init.env
sh -x /dlts-runtime/install.sh

echo bootstrap starts at `date`

# https://stackoverflow.com/a/26759734/845762
if ! [ -x "$(command -v sudo)" ] ; then
    time apt-get update && time apt-get --no-install-recommends install -y sudo
fi

bash ${CWD}/init_user.sh
bash ${CWD}/setup_sshd.sh
bash ${CWD}/setup_ssh_config.sh

echo bootstrap ends at `date`

mkdir -p /dlts-runtime/status
touch /dlts-runtime/status/READY

set +e
# Execute user's command for the job
if [ "$DLTS_ROLE_NAME" = "worker" ];
then
    runuser -l ${DLTS_USER_NAME} -c "sleep infinity"
else
    printenv DLTS_LAUNCH_CMD > /dlts-runtime/status/job_command.sh
    chmod +x /dlts-runtime/status/job_command.sh
    runuser -l ${DLTS_USER_NAME} -c /dlts-runtime/status/job_command.sh
    # Save exit code
    EXIT_CODE=$?
    echo  `date` ": ${EXIT_CODE}"
fi

# exit
exit ${EXIT_CODE}
