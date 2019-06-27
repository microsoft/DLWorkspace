import sys
import os
from datetime import date
from marshmallow import Schema, fields, pprint, post_load, validate

import logging
import logging.config

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../utils"))
from osUtils import mkdirsAsUser


# TODO remove it latter
def create_log(logdir='.'):
    if not os.path.exists(logdir):
        os.system("mkdir -p " + logdir)
    with open('logging.yaml') as f:
        logging_config = yaml.load(f)
        f.close()
        logging_config["handlers"]["file"]["filename"] = logdir + "/jobmanager.log"
        logging.config.dictConfig(logging_config)


class Job:
    def __init__(self,
                 cluster,
                 job_id,
                 email,
                 mountpoints=None,
                 job_path="",
                 work_path="",
                 data_path="",
                 ):
        """
        job_id: an unique string for the job.
        email: user's email.
        cluster: cluster config.
        job_path: relative path, on shared storage, for example "user_alias/jobs/date/job_id".
        work_path: relative path, on shared storage, for example "user_alias".
        """
        self.cluster = cluster
        self.job_id = job_id
        self.email = email
        self.mountpoints = mountpoints
        self.job_path = job_path
        self.work_path = work_path
        self.data_path = data_path

    def add_mountpoints(self, mountpoint):
        '''
        1. Silently skip if the name/hostPath/containerPath duplicates with an existing one.
        2. Name would be normalized.

        Mountpoint example:
            {
            "enabled":true,
            "containerPath":"/home/username",
            "hostPath":"/dlwsdata/work/username",
            "name":"homefolder"
            }
        '''
        if mountpoint is None:
            return
        if self.mountpoints is None:
            self.mountpoints = []

        # add each items in the list one by one
        if isinstance(mountpoint, list):
            for m in mountpoint:
                self.add_mountpoints(m)
                return

        # only allow alphanumeric in "name"
        if "name" not in mountpoint or mountpoint["name"] == "":
            mountpoint["name"] = mountpoint["containerPath"]
        mountpoint["name"] = ''.join(c for c in mountpoint["name"] if c.isalnum())

        # skip dulicate entry
        for item in self.mountpoints:
            if item["name"] == mountpoint["name"] or item["containerPath"] == mountpoint["containerPath"] or item["hostPath"] == mountpoint["hostPath"]:
                logging.warn("Duplciate mountpoint: %s" % mountpoint)
                return

        self.mountpoints.append(mountpoint)

    def get_alias(self):
        return self.email.split("@")[0].strip()

    def get_homefolder_hostpath(self):
        return os.path.join(self.cluster["storage-mount-path"], "work/", self.get_alias())

    def get_job_path_hostpath(self):
        return os.path.join(self.cluster["storage-mount-path"], "work/", self.job_path)

    def job_path_mountpoint(self):
        assert(len(self.job_path) > 0)
        job_host_path = os.path.join(self.cluster["storage-mount-path"], "work", self.job_path)
        return {"name": "job", "containerPath": "/job", "hostPath": job_host_path, "enabled": True}

    def work_path_mountpoint(self):
        assert(len(self.work_path) > 0)
        work_host_path = os.path.join(self.cluster["storage-mount-path"], "work", self.work_path)
        return {"name": "work", "containerPath": "/work", "hostPath": work_host_path, "enabled": True}

    def data_path_mountpoint(self):
        assert(self.data_path is not None)
        data_host_path = os.path.join(self.cluster["storage-mount-path"], "storage", self.data_path)
        return {"name": "data", "containerPath": "/data", "hostPath": data_host_path, "enabled": True}

    def generate_launch_script(self, path_to_save, user_id, gpu_num, user_script):
        if not os.path.exists(path_to_save):
            mkdirsAsUser(path_to_save, user_id)

        file_name = "launch-%s.sh" % self.job_id
        launch_script_file = os.path.join(path_to_save, file_name)
        with open(launch_script_file, 'w') as f:
            f.write("#!/bin/bash -x\n")
            f.write("mkdir /opt; \n")
            f.write("echo 'localhost slots=%s' | tee -a /opt/hostfile; \n" % gpu_num)
            f.write("bash /dlws/init_user.sh &> /job/init_user_script.log && runuser -l ${DLWS_USER_NAME} -c '%s'\n" % user_script)
        os.system("sudo chown %s %s" % (user_id, launch_script_file))
        return file_name


class JobSchema(Schema):
    cluster = fields.Dict(required=True)
    job_id = fields.String(required=True,
                           # Correctly mappging the name
                           dump_to="jobId", load_from="jobId",
                           # We use the id as "name" in k8s object.
                           # By convention, the "names" of Kubernetes resources should be
                           #  up to maximum length of 253 characters and consist of lower case
                           # alphanumeric characters, -, and .,
                           # but certain resources have more specific restrictions.
                           validate=validate.Regexp(r'^[a-z0-9]([-a-z0-9]*[a-z0-9])?$',
                                                    error="'{input}' does not match expected pattern {regex}."))
    email = fields.Email(required=True, dump_to="userName", load_from="userName")
    mountpoints = fields.Dict(required=False)
    job_path = fields.String(required=False, dump_to="jobPath", load_from="jobPath")
    work_path = fields.String(required=False, dump_to="workPath", load_from="workPath")
    data_path = fields.String(required=False, dump_to="dataPath", load_from="dataPath")

    @post_load
    def make_user(self, data, **kwargs):
        return Job(**data)
