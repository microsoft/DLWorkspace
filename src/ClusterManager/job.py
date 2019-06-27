import sys
import os
from datetime import date
from marshmallow import Schema, fields, pprint, post_load, validate

import logging
import logging.config

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../utils"))

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
    def __init__(self, job_id, mountpoints=None):
        self.job_id = job_id
        self.mountpoints = mountpoints

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


class JobSchema(Schema):
    job_id = fields.String(required=True,
                           # Correctly mappging the name
                           dump_to="jobId", load_from="jobId",
                           # We use the id as "name" in k8s object.
                           # By convention, the "names" of Kubernetes resources should be
                           #  up to maximum length of 253 characters and consist of lower case
                           # alphanumeric characters, -, and ., but certain resources have more specific restrictions.
                           validate=validate.Regexp(r'^[a-z0-9]([-a-z0-9]*[a-z0-9])?$', 0, error="'{input}' does not match expected pattern {regex}."))
    mountpoints = fields.Dict(required=False)

    @post_load
    def make_user(self, data, **kwargs):
        return Job(**data)
