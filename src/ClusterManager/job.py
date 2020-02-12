#!/usr/bin/env python3

import os
import random
import json
import logging
import logging.config
import base64

from marshmallow import Schema, fields, post_load, validate
from jinja2 import Environment, FileSystemLoader, Template

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
        self.mountpoints = mountpoints
        self.nfs_mountpoints = []
        self.job_path = job_path
        self.work_path = work_path
        self.data_path = data_path
        self.params = params
        self.plugins = plugins

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
        mountpoint["name"] = ''.join(c for c in mountpoint["name"]
                                     if c.isalnum() or c == "-")

        # skip duplicate entry
        # NOTE: mountPath "/data" is the same as "data" in k8s
        for item in self.mountpoints:
            if item["name"] == mountpoint["name"] or item[
                    "containerPath"].strip(
                        "/") == mountpoint["containerPath"].strip("/"):
                logger.warn(
                    "Current mountpoint: %s is a duplicate of mountpoint: %s" %
                    (mountpoint, item))
                return

        self.mountpoints.append(mountpoint)

    def add_nfs_mountpoints(self, nfs_mountpoint):
        """ Adds unique nfs_mountpoint with a normalized name.

        1. Skip if either of the following is true:
           - name of the nfs_mountpoint already exists.
           - mountPath of the nfs_mountpoint already exists in the same VC
        2. A normalized name only contains alphanumeric character or dash.
        Args:
            nfs_mountpoint: An nfs_mountpoint or a list of nfs_mountpoints

        nfs nfs_mountpoint example:
        {
            "name": mountpoint0,  # optional
            "enabled": True,
            "server": 192.168.0.10,
            "path": /data/share/storage,
            "mountPath": /data,
            "vc": platform,  # optional
        }

        Returns:
            None
        """
        # Skip None
        if nfs_mountpoint is None:
            logger.warning("Skip None nfs_mountpoint")
            return

        # add each items in the list one by one
        if isinstance(nfs_mountpoint, list):
            for m in nfs_mountpoint:
                self.add_mountpoints(m)
            return

        # Skip invalid nfs_mountpoint
        enabled = nfs_mountpoint.get("enabled")
        server = nfs_mountpoint.get("server")
        path = nfs_mountpoint.get("path")
        mount_path = nfs_mountpoint.get("mountPath")
        if invalid_entry(enabled) or \
                invalid_entry(server) or \
                invalid_entry(path) or \
                invalid_entry(mount_path):
            logger.warning("Skip invalid nfs_mountpoint %s", nfs_mountpoint)
            return

        # only allow alphanumeric and dash in "name"
        name = nfs_mountpoint.get("name")
        vc = nfs_mountpoint.get("vc")
        if invalid_entry(name):
            vc_prefix = "" if invalid_entry(vc) else "%s-" % vc
            name = "%s%s" % (vc_prefix, mount_path)
        nfs_mountpoint["name"] = "".join(
            [c for c in name if c.isalnum() or c == "-"]
        ).lower()

        if not self._nfs_mountpoint_exists(nfs_mountpoint):
            self.nfs_mountpoints.append(nfs_mountpoint)

    def _nfs_mountpoint_exists(self, nfs_mountpoint):
        name = nfs_mountpoint.get("name")
        mount_path = nfs_mountpoint.get("mountPath")
        vc = nfs_mountpoint.get("vc")

        # NOTE: mountPath "/data" is the same as "data" in k8s
        for item in self.nfs_mountpoints:
            dup_name = item.get("name") == name
            dup_mount_path = \
                item.get("mountPath").strip("/") == mount_path.strip("/") and \
                item.get("vc") == vc
            if dup_name or dup_mount_path:
                return True
        return False

    def _mountpoint_in_nfs_mountpoints(self, mountpoint):
        # Function to check if a hostPath mountpoint already exists in
        # self.nfs_mountpoints. Used to migrate NFS mount from hostPath to
        # kubernetes NFS plugin
        container_path = mountpoint.get("containerPath")
        mountpoint["mountPath"] = container_path
        return self._nfs_mountpoint_exists(mountpoint)

    def add_plugins(self, plugins):
        self.plugins = plugins

    def get_alias(self):
        return self.email.split("@")[0].strip()

    def get_hostpath(self, *path_relate_to_workpath):
        """return os.path.join(self.cluster["storage-mount-path"], "work", *path_relate_to_workpath)"""
        return os.path.join(self.cluster["storage-mount-path"], "work",
                            *path_relate_to_workpath)

    def get_homefolder_hostpath(self):
        return self.get_hostpath(self.get_alias())

    def job_path_mountpoint(self):
        assert (len(self.job_path) > 0)
        job_host_path = self.get_hostpath(self.job_path)
        return {
            "name": "job",
            "containerPath": "/job",
            "hostPath": job_host_path,
            "enabled": True
        }

    def work_path_mountpoint(self):
        assert (len(self.work_path) > 0)
        work_host_path = self.get_hostpath(self.work_path)
        return {
            "name": "work",
            "containerPath": "/work",
            "hostPath": work_host_path,
            "enabled": True
        }

    def data_path_mountpoint(self):
        assert (self.data_path is not None)
        data_host_path = os.path.join(self.cluster["storage-mount-path"],
                                      "storage", self.data_path)
        return {
            "name": "data",
            "containerPath": "/data",
            "hostPath": data_host_path,
            "enabled": True
        }

    def nfs_mountpoints_for_job(self):
        """Returns all nfs mountpoints for this job, including global and vc.
        """
        vc_name = self.params["vcName"]
        nfs_mountpoints = [
            mountpoint for mountpoint in self.get_nfs_mountpoints()
            if mountpoint.get("vc") is None or mountpoint.get("vc") == vc_name
        ]

        for mountpoint in nfs_mountpoints:
            mountpoint["enabled"] = True
        return nfs_mountpoints

    def vc_custom_storage_mountpoints(self):
        vc_name = self.params["vcName"]
        custom_mounts = self.get_custom_mounts()
        if not isinstance(custom_mounts, list):
            return None

        vc_custom_mounts = []
        for mount in custom_mounts:
            name = mount.get("name")
            container_path = mount.get("containerPath")
            host_path = mount.get("hostPath")
            vc = mount.get("vc")
            if vc is None or vc != vc_name:
                continue
            if name is None or host_path is None or container_path is None:
                logger.warning("Ignore invalid mount %s", mount)
                continue
            vc_mount = {
                "name": name.lower(),
                "containerPath": container_path,
                "hostPath": host_path,
                "enabled": True,
                "vc": vc_name,
            }

            if not self._mountpoint_in_nfs_mountpoints(vc_mount):
                vc_custom_mounts.append(vc_mount)

        return vc_custom_mounts

    def vc_storage_mountpoints(self):
        vc_name = self.params["vcName"]
        dltsdata_vc_path = os.path.join(
            self.cluster["dltsdata-storage-mount-path"], vc_name)
        if not os.path.isdir(dltsdata_vc_path):
            return None

        vc_mountpoints = []
        for storage in os.listdir(dltsdata_vc_path):
            vc_mountpoint = {
                "name": ("%s-%s" % (vc_name, storage)).lower(),
                "containerPath": "/" + storage,
                "hostPath": os.path.join(dltsdata_vc_path, storage),
                "enabled": True,
                "vc": vc_name,
            }

            if not self._mountpoint_in_nfs_mountpoints(vc_mountpoint):
                vc_mountpoints.append(vc_mountpoint)

        return vc_mountpoints

    def infiniband_mountpoints(self):
        infiniband_mounts = self.get_infiniband_mounts()
        if not isinstance(infiniband_mounts, list):
            return None

        ib_mountpoints = []
        for infiniband_mount in infiniband_mounts:
            ib_mountpoint = {
                "name": infiniband_mount["name"].lower(),
                "containerPath": infiniband_mount["containerPath"],
                "hostPath": infiniband_mount["hostPath"],
                "enabled": True
            }
            ib_mountpoints.append(ib_mountpoint)

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

    def get_custom_mounts(self):
        return self._get_cluster_config("custom_mounts")

    def get_infiniband_mounts(self):
        return self._get_cluster_config("infiniband_mounts")

    def get_local_fast_storage(self):
        return self._get_cluster_config("local_fast_storage")

    def get_enable_blobfuse(self):
        return self._get_cluster_config("enable_blobfuse")

    def get_enable_custom_registry_secrets(self):
        return self._get_cluster_config("enable_custom_registry_secrets")

    def get_nccl_ib_disable(self):
        return self._get_cluster_config("nccl_ib_disable")

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

    def get_nfs_mountpoints(self):
        nfs_mountpoints = self._get_cluster_config("nfs_mountpoints")
        if nfs_mountpoints is None or not isinstance(nfs_mountpoints, list):
            nfs_mountpoints = []
        return nfs_mountpoints

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

        blobfuse = []
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
                bf["root_tmppath"] = root_tmppath
                bf["tmppath"] = name

            # Also support a list of strings
            if isinstance(mount_options, list):
                mount_options = " ".join(mount_options)

            if not invalid_entry(mount_options):
                bf["mountOptions"] = mount_options

            # TODO: Deduplicate blobfuse plugins
            blobfuse = dedup_add(bf, blobfuse, identical)
        return blobfuse

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
