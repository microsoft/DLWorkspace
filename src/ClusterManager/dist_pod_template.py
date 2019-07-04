import json
import yaml
from jinja2 import Template
from job import Job


class DistPodTemplate():
    def __init__(self, template, enable_custom_scheduler=False):
        self.template = template
        self.enable_custom_scheduler = enable_custom_scheduler

    @staticmethod
    def generate_launch_cmd(role, user_alias, job_path, worker_num, cmd):
        # change ssh folder permission here because the setup permission
        #  script in launch_ps_job function may have race condition with init_user.sh script.
        # results in no such user error
        if role == "ps":
            launchCMD = """
#!/bin/bash
echo "[DLWorkspace System]: Waiting for all containers are ready..."
while [ ! -f /opt/run_dist_job ]; do
    sleep 3
done

sudo chmod 600 -R /home/{0}/.ssh &>/dev/null;
sudo chmod 700 /home/{0}/.ssh &>/dev/null;
sudo chown -R {0} /home/{0}/.ssh &>/dev/null;

sudo mkdir -p /root/.ssh  &>/dev/null ;
sudo ln -s /home/{0}/.ssh/config /root/.ssh/config  &>/dev/null;
sudo mkdir -p /opt  &>/dev/null;
sudo ln -s /job/hostfile /opt/hostfile &>/dev/null;

JOB_DIR='/home/{1}'
WORKER_NUM={2}
echo $JOB_DIR $WORKER_NUM

all_workers_ready=false
while [ "$all_workers_ready" != true ]
do
  # update it to false if any woker is not ready
  all_workers_ready=true

  for i in $(seq 0 $(( ${{WORKER_NUM}} - 1)) )
  do
    worker="worker${{i}}"
    file="$JOB_DIR/${{worker}}/WORKER_READY"
    #echo $file

    if [ ! -f $file ]; then
      echo "${{worker}} not ready!"
      all_workers_ready=false
      sleep 10
    fi
  done
done

echo "[DLWorkspace System]: All containers are ready, launching training job..."
{3}
""".format(user_alias, job_path, worker_num, cmd)
        else:
            launchCMD = """
while [ ! -f /opt/run_dist_job ]; do
    sleep 3
done
sudo chmod 600 -R /home/{0}/.ssh &>/dev/null;
sudo chmod 700 /home/{0}/.ssh &>/dev/null;
sudo chown -R {0} /home/{0}/.ssh  &>/dev/null;
sudo mkdir -p /root/.ssh  &>/dev/null;
sudo ln -s /home/{0}/.ssh/config /root/.ssh/config &>/dev/null;
sudo mkdir -p /opt && sudo ln -s /job/hostfile /opt/hostfile  &>/dev/null;

# TODO mark the worker as 'READY', better to change to '/pod/READY' later
sudo touch /job/WORKER_READY

sleep infinity
""".format(user_alias)
        return launchCMD
