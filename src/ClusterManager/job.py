#!/usr/bin/env python3

import copy
import os
import random
import json
import logging
import logging.config
import base64

from marshmallow import Schema, fields, post_load, validate
from jinja2 import Environment, FileSystemLoader, Template
from mountpoint import MountPoint, make_mountpoint

logger = logging.getLogger(__name__)


def invalid_entry(s):
    return s is None or \
        s == "" or \
        s.lower() == "null" or \
        s.lower() == "none"


def dedup_add(item, entries, identical):
    assert isinstance(entries, list)
    for entry in entries:
        if identical(item, entry):
            return entries
    entries.append(item)
    return entries


def b64encode(str_val):
    return base64.b64encode(str_val.encode("utf-8")).decode("utf-8")


class Job:
    def __init__(self,
                 cluster,
                 job_id,
                 email,
                 mountpoints=None,
                 job_path="",
                 work_path="",
                 data_path="",
                 params=None,
                 plugins=None):
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

        self.mountpoints = None
        self.add_mountpoints(mountpoints)

        self.job_path = job_path
        self.work_path = work_path
        self.data_path = data_path
        self.params = params
        self.plugins = plugins

    def add_mountpoints(self, mountpoint):
        """Adds unique mountpoint to job_mountpoints.

        Args:
            mountpoint: A MountPoint object

        Returns:
            None
        """
        if mountpoint is None:
            return

        if self.mountpoints is None:
            self.mountpoints = []

        if isinstance(mountpoint, list):
            for mp in mountpoint:
                self.add_mountpoints(mp)
            return

        # Skip invalid mountpoint
        if not mountpoint.is_valid():
            logger.warning("Skip invalid mountpoint %s", mountpoint)
            return

        if not self._mountpoint_exists_in(mountpoint):
            self.mountpoints.append(mountpoint)

    def _mountpoint_exists_in(self, mountpoint):
        # Consider None as present in order not to add None
        if mountpoint is None:
            return True

        # If an equal mountpoint is found, then the mountpoint is present.
        for mp in self.mountpoints:
            if mountpoint == mp:
                logger.warning("mountpoint %s is a duplicate of an existing "
                               "mountpoint %s", mountpoint, mp)
                return True
        return False

    def get_cluster_nfs(self):
        cluster_nfs = self._get_cluster_config("cluster_nfs")
        assert cluster_nfs is not None, "cluster_nfs in config cannot be None"
        return cluster_nfs

    def get_cluster_nfs_server(self):
        return self.get_cluster_nfs()["server"]

    def get_cluster_nfs_path(self):
        return self.get_cluster_nfs()["path"]

    def get_nfs_path_with_folder(self, folder, *rel_path):
        """Returns cluster shared NFS path for a folder and a relative path."""
        nsf_path = self.get_cluster_nfs_path()
        return os.path.join(nsf_path, folder, *rel_path)

    def get_homefolder_nfs_path(self):
        return self.get_nfs_path_with_folder("work", self.get_alias())

    def home_path_nfs_mountpoint(self):
        alias = self.get_alias()
        server = self.get_cluster_nfs_server()
        path = self.get_nfs_path_with_folder("work", alias)
        mp = make_mountpoint(params={
            "name": "home",
            "mountPath": "/home/%s" % alias,
            "mountType": "nfs",
            "server": server,
            "path": path
        })
        logger.info("job %s has home path nfs mountpoint: %s", self.job_id, mp)
        return mp

    def job_path_nfs_mountpoint(self):
        assert isinstance(self.job_path, str) and len(self.job_path) > 0
        server = self.get_cluster_nfs_server()
        path = self.get_nfs_path_with_folder("work", "")
        mp = make_mountpoint(params={
            "name": "job",
            "mountPath": "/job",
            "mountType": "nfs",
            "server": server,
            "path": path,
            "subPath": self.job_path,
        })
        logger.info("job %s has job path nfs mountpoint: %s", self.job_id, mp)
        return mp

    def work_path_nfs_mountpoint(self):
        assert isinstance(self.work_path, str) and len(self.work_path) > 0
        server = self.get_cluster_nfs_server()
        path = self.get_nfs_path_with_folder("work", self.work_path)
        mp = make_mountpoint(params={
            "name": "work",
            "mountPath": "/work",
            "mountType": "nfs",
            "server": server,
            "path": path
        })
        logger.info("job %s has work path nfs mountpoint: %s", self.job_id, mp)
        return mp

    def data_path_nfs_mountpoint(self):
        assert isinstance(self.data_path, str)
        server = self.get_cluster_nfs_server()
        path = self.get_nfs_path_with_folder("storage", self.data_path)
        mp = make_mountpoint(params={
            "name": "data",
            "mountPath": "/data",
            "mountType": "nfs",
            "server": server,
            "path": path
        })
        logger.info("job %s has data path nfs mountpoint: %s", self.job_id, mp)
        return mp

    def system_mountpoints(self):
        """Returns all system defined mountpoints for this job. They can be
        NFS mountpoints, hostPath mountpoints, and many to be defined. If vc is
        undefined, the mountpoint is a cluster shared mountpoint.
        """
        vc_name = self.params["vcName"]
        mp_params = [mp for mp in self.get_system_mountpoints()
                     if mp.get("vc") is None or mp.get("vc") == vc_name]
        mps = []
        for mp_param in mp_params:
            mp = make_mountpoint(mp_param)
            if mp is not None:
                logger.info("job %s has mountpoint: %s", self.job_id, mp)
                mps.append(mp)
            else:
                logger.warning("job %s has mountpoint for param %s None",
                               self.job_id, mp_param)
        return mps

    def add_plugins(self, plugins):
        self.plugins = plugins

    def get_alias(self):
        return self.email.split("@")[0].strip()

    def get_hostpath(self, *path_relate_to_workpath):
        return os.path.join(self.cluster["storage-mount-path"], "work",
                            *path_relate_to_workpath)

    def infiniband_mountpoints(self):
        infiniband_mounts = self.get_infiniband_mounts()
        if not isinstance(infiniband_mounts, list):
            return None

        ib_mountpoints = []
        for infiniband_mount in infiniband_mounts:
            ib_mp = make_mountpoint(params={
                "name": infiniband_mount["name"].lower(),
                "mountPath": infiniband_mount["containerPath"],
                "hostPath": infiniband_mount["hostPath"],
                "mountType": "hostPath",
            })
            ib_mountpoints.append(ib_mp)

        return ib_mountpoints

    def get_template(self):
        """Returns pod template."""
        return self._get_template("pod.yaml.template")

    def get_deployment_template(self):
        """Returns deployment template."""
        return self._get_template("deployment.yaml.template")

    def get_blobfuse_secret_template(self):
        """Returns azure blobfuse secret template."""
        return self._get_template("blobfuse_secret.yaml.template")

    def get_image_pull_secret_template(self):
        """Returns image pull secret template."""
        return self._get_template("image_pull_secret.yaml.template")

    def _get_template(self, template_name):
        """Returns template instance based on template_name."""
        path = os.path.abspath(
            os.path.join(self.cluster["root-path"], "Jobs_Templete",
                         template_name))
        env = Environment(loader=FileSystemLoader("/"))
        template = env.get_template(path)
        assert (isinstance(template, Template))
        return template

    def get_pod_ip_range(self):
        return self._get_cluster_config("pod_ip_range")

    def get_infiniband_mounts(self):
        return self._get_cluster_config("infiniband_mounts")

    def get_local_fast_storage(self):
        return self._get_cluster_config("local_fast_storage")

    def get_enable_blobfuse(self):
        return self._get_cluster_config("enable_blobfuse")

    def get_enable_custom_registry_secrets(self):
        return self._get_cluster_config("enable_custom_registry_secrets")

    def get_distributed_system_envs(self):
        distributed_system_envs = \
            self._get_cluster_config("distributed_system_envs")
        if distributed_system_envs is None or \
                not isinstance(distributed_system_envs, dict):
            distributed_system_envs = {}
        return distributed_system_envs

    def get_vc_node_hard_assignment(self):
        return self._get_cluster_config("vc_node_hard_assignment")

    def get_vc_without_shared_storage(self):
        """Special VCs that do not have /data and /work"""
        vc_without_shared_storage = self._get_cluster_config(
            "vc_without_shared_storage")
        if vc_without_shared_storage is None or \
                not isinstance(vc_without_shared_storage, list):
            vc_without_shared_storage = []
        return vc_without_shared_storage

    def get_system_mountpoints(self):
        system_mountpoints = self._get_cluster_config("system_mountpoints")
        if system_mountpoints is None or \
                not isinstance(system_mountpoints, list):
            system_mountpoints = []
        return system_mountpoints

    def _get_cluster_config(self, key):
        if key in self.cluster:
            return self.cluster[key]
        return None

    def get_plugins(self):
        """Returns a dictionary of plugin list.

        NOTE: Currently only Azure blobfuse is supported.

        Returns:
            A dictionary of plugin list.
            Empty dictionary if there is no plugin.

        Examples:
            {
                "blobfuse":
                    [{
                        "enabled": True,
                        "name": "blobfuse0",
                        "accountName": "YWRtaW4=",
                        "accountKey": "MWYyZDFlMmU2N2Rm",
                        "containerName": "blobContainer0",
                        "mountPath": "/mnt/blobfuse/data0",
                        "secreds": "bb9cd821-711c-40fd-bb6f-e5dbc1b772a7-blobfuse-0-secreds",
                        "mountoptions": (optional),
                        "tmppath": system-defined (optional)
                     },
                     {
                        "enabled": True,
                        "name": "blobfuse1",
                        "accountName":"YWJj",
                        "accountKey":"cGFzc3dvcmQ=",
                        "containerName":"blobContainer1",
                        "mountPath":"/mnt/blobfuse/data1",
                        "secreds":"bb9cd821-711c-40fd-bb6f-e5dbc1b772a7-blobfuse-1-secreds",
                        "mountoptions": (optional),
                        "tmppath": system-defined (optional)
                     }],
                "some-other-plugin": [...]
            }
        """
        if self.params is None:
            return {}

        if "plugins" not in self.params:
            return {}

        plugins = self.params["plugins"]
        if plugins is None or not isinstance(plugins, dict):
            return {}

        ret = {}
        for plugin, plugin_config in list(plugins.items()):
            if plugin == "blobfuse" and isinstance(plugin_config, list):
                blobfuse = self.get_blobfuse_plugins(plugin_config)
                ret["blobfuse"] = blobfuse
            elif plugin == "imagePull" and isinstance(plugin_config, list):
                image_pulls = self.get_image_pull_secret_plugins(plugin_config)
                ret["imagePull"] = image_pulls
        return ret

    def get_blobfuse_plugins(self, plugins):
        """Constructs and returns a list of blobfuse plugins."""

        enable_blobfuse = self.get_enable_blobfuse()
        if enable_blobfuse is None or enable_blobfuse is False:
            return []

        def identical(e1, e2):
            return e1["name"] == e2["name"] or \
                e1["mountPath"] == e2["mountPath"]

        root_tmppath = None
        local_fast_storage = self.get_local_fast_storage()
        if local_fast_storage is not None and local_fast_storage != "":
            root_tmppath = local_fast_storage.rstrip("/")

        blobfuses = []
        for i, p_bf in enumerate(plugins):
            account_name = p_bf.get("accountName")
            account_key = p_bf.get("accountKey")
            container_name = p_bf.get("containerName")
            mount_path = p_bf.get("mountPath")
            mount_options = p_bf.get("mountOptions")

            # Ignore Azure blobfuse with incomplete configurations
            if invalid_entry(account_name) or \
                    invalid_entry(account_key) or \
                    invalid_entry(container_name) or \
                    invalid_entry(mount_path):
                continue

            name = p_bf.get("name")
            if name is None:
                name = "%s-blobfuse-%d" % (self.job_id, i)

            # Reassign everything for clarity
            bf = {
                "enabled": True,
                "name": name,
                "secreds": "%s-blobfuse-%d-secreds" % (self.job_id, i),
                "accountName": b64encode(account_name),
                "accountKey": b64encode(account_key),
                "containerName": container_name,
                "mountPath": mount_path,
                "jobId": self.job_id,
            }

            if root_tmppath is not None:
                # Make tmppath unique for each blobfuse mount
                bf["rootTmppath"] = root_tmppath
                bf["tmppath"] = name

            # Also support a list of strings
            if isinstance(mount_options, list):
                mount_options = " ".join(mount_options)

            if not invalid_entry(mount_options):
                bf["mountOptions"] = mount_options

            # TODO: Refactor into mountpoint add
            blobfuses = dedup_add(bf, blobfuses, identical)

            # Add to mountpoints
            bf["mountType"] = "blobfuse"
            bf_mp = make_mountpoint(bf)
            if bf_mp is not None:
                self.add_mountpoints(bf_mp)

        return blobfuses

    def get_image_pull_secret_plugins(self, plugins):
        """Constructs and returns a list of imagePullSecrets plugins."""

        is_enabled = self.get_enable_custom_registry_secrets()
        if is_enabled is None or is_enabled is False:
            return []

        image_pull_secrets = []
        for i, image_pull in enumerate(plugins):
            registry = image_pull.get("registry")
            username = image_pull.get("username")
            password = image_pull.get("password")

            if invalid_entry(registry) or \
                    invalid_entry(username) or \
                    invalid_entry(password):
                continue

            auth = b64encode(("%s:%s" % (username, password)))

            auths = {"auths": {registry: {"auth": auth}}}

            dockerconfigjson = b64encode(json.dumps(auths))

            secret = {
                "enabled": True,
                "name": "%s-imagepull-%d-secreds" % (self.job_id, i),
                "dockerconfigjson": dockerconfigjson,
                "jobId": self.job_id
            }
            image_pull_secrets.append(secret)

        return image_pull_secrets

    def get_image_pull_secret_plugins(self, plugins):
        """Constructs and returns a list of imagePullSecrets plugins."""

        enable_custom_registry_secrets = self.get_enable_custom_registry_secrets()
        if enable_custom_registry_secrets is None or \
                enable_custom_registry_secrets is False:
            return []

        image_pull_secrets = []
        for i, image_pull in enumerate(plugins):
            registry = image_pull.get("registry")
            username = image_pull.get("username")
            password = image_pull.get("password")

            if invalid_entry(registry) or \
                    invalid_entry(username) or \
                    invalid_entry(password):
                continue

            auth = base64.b64encode("%s:%s" % (username, password))

            auths = {
                "auths": {
                    registry: {
                        "auth": auth
                    }
                }
            }

            dockerconfigjson = base64.b64encode(json.dumps(auths))

            secret = {
                "enabled": True,
                "name": "%s-imagepull-%d-secreds" % (self.job_id, i),
                "dockerconfigjson": dockerconfigjson,
                "jobId": self.job_id
            }
            image_pull_secrets.append(secret)

        return image_pull_secrets


class JobSchema(Schema):
    cluster = fields.Dict(required=True)
    job_id = fields.String(
        required=True,
        # Correctly mappging the name
        dump_to="jobId",
        load_from="jobId",
        # We use the id as "name" in k8s object.
        # By convention, the "names" of Kubernetes resources should be
        #  up to maximum length of 253 characters and consist of lower case
        # alphanumeric characters, -, and .,
        # but certain resources have more specific restrictions.
        validate=validate.Regexp(
            r'^[a-z0-9]([-a-z0-9]*[a-z0-9])?$',
            error="'{input}' does not match expected pattern {regex}."))
    email = fields.Email(required=True,
                         dump_to="userName",
                         load_from="userName")
    mountpoints = fields.Dict(required=False)
    job_path = fields.String(required=False,
                             dump_to="jobPath",
                             load_from="jobPath")
    work_path = fields.String(required=False,
                              dump_to="workPath",
                              load_from="workPath")
    data_path = fields.String(required=False,
                              dump_to="dataPath",
                              load_from="dataPath")
    params = fields.Dict(required=False)
    plugins = fields.Dict(required=False)

    @post_load
    def make_user(self, data, **kwargs):
        return Job(**data)
