#! /bin/bash
set -ex

. /dlts-runtime/env/init.env
sh -x /dlts-runtime/install.sh

SCRIPT_DIR=/pod/scripts

echo bootstrap starts at `date` &>> ${LOG_DIR}/bootstrap.log

if [ "$DLWS_ROLE_NAME" != "inferenceworker" ];
then
	# Dir for saving running status
	export PROC_DIR=/pod/running
	rm -rf ${PROC_DIR}
	mkdir -p ${PROC_DIR}

	# Dir for logs
	export LOG_DIR=/pod/logs
	rm -rf ${LOG_DIR}
	mkdir -p ${LOG_DIR}

	# Save the pid.
	PID_FILE=${PROC_DIR}/pid
	echo $$ > $PID_FILE
fi

# Setup container
bash ${SCRIPT_DIR}/init_user.sh &>> ${LOG_DIR}/bootstrap.log

if [ "$DLWS_ROLE_NAME" != "inferenceworker" ];
then
	touch ${PROC_DIR}/CONTAINER_READY
fi

# Setup roles
bash ${SCRIPT_DIR}/setup_sshd.sh &>> ${LOG_DIR}/bootstrap.log

if [ "$DLWS_ROLE_NAME" != "inferenceworker" ];
then
    bash ${SCRIPT_DIR}/setup_ssh_config.sh &>> ${LOG_DIR}/bootstrap.log
	touch ${PROC_DIR}/ROLE_READY

	# Setup job
	# TODO
	touch ${PROC_DIR}/JOB_READY
fi

echo bootstrap ends at `date` &>> ${LOG_DIR}/bootstrap.log

set +e
# Execute user's command for the job
if [ "$DLWS_ROLE_NAME" = "worker" ];
then
    runuser -l ${DLWS_USER_NAME} -c "sleep infinity"
else
    printenv DLWS_LAUNCH_CMD > /pod/job_command.sh
    chmod +x /pod/job_command.sh
    runuser -l ${DLWS_USER_NAME} -c /pod/job_command.sh
    # Save exit code
    EXIT_CODE=$?
    echo  `date` ": ${EXIT_CODE}"  > ${PROC_DIR}/EXIT_CODE
fi

# exit
exit ${EXIT_CODE}
