#!/usr/bin/env python3

import logging
import collections
import copy
import re

logger = logging.getLogger(__name__)

class Resource(object):
    def __init__(self, cpu_req, mem_req, cpu_limit, mem_limit, gpu_limit, gpu_type):
        self.cpu_req = cpu_req
        self.mem_req = mem_req
        self.cpu_limit = cpu_limit
        self.mem_limit = mem_limit
        self.gpu_limit = gpu_limit
        self.gpu_type = gpu_type

class Role(object):
    def __init__(self, name, task_count, image, envs, resource,
            min_failed_task_count, succeeded_task_count):
        self.name = name
        self.task_count = task_count
        self.image = image
        self.envs = envs
        self.resource = resource
        self.min_failed_task_count = min_failed_task_count
        self.succeeded_task_count = succeeded_task_count

# FIXME with pod_name, we may can not use blobfuse

class Framework(object):
    def __init__(self, init_image, labels, annotations, roles, job_id, pod_name, user_cmd,
            alias, email, gid, uid, mount_points, plugins, family_token, vc_name,
            dns_policy, node_selector, home_folder_host_path,
            is_fragment_gpu_job, is_preemption_allowed,
            is_host_network, is_host_ipc, is_privileged, is_nccl_ib_disabled):
        self.init_image = init_image # str
        self.labels = labels # map
        self.annotations = annotations # map
        self.roles = roles # a map, key is role name, value is Role object
        self.job_id = job_id # str
        self.pod_name = pod_name # str
        self.user_cmd = user_cmd # str
        self.alias = alias # str
        self.email = email # str
        self.gid = gid # str
        self.uid = uid #str
        self.mount_points = mount_points
        self.plugins = plugins
        self.family_token = family_token # str
        self.vc_name = vc_name # str
        self.dns_policy = dns_policy # str
        self.node_selector = node_selector # map
        self.home_folder_host_path = home_folder_host_path # str
        self.is_fragment_gpu_job = is_fragment_gpu_job # bool
        self.is_preemption_allowed = is_preemption_allowed # bool
        self.is_host_network = is_host_network # bool
        self.is_host_ipc = is_host_ipc # bool
        self.is_privileged = is_privileged # bool
        self.is_nccl_ib_disabled = is_nccl_ib_disabled # bool


def gen_init_container(job, role):
    ps_count = worker_count = 0
    if job.roles.get("ps") is not None:
        ps_count = job.roles["ps"].task_count
    if job.roles.get("worker") is not None:
        worker_count = job.roles["worker"].task_count
    else:
        worker_count = 1 # regular job, role will be master

    envs = [
            {"name": "LOGGING_LEVEL", "value": "DEBUG"},
            {"name": "DLWS_JOB_ID", "value": str(job.job_id)},
            {"name": "DLWS_NUM_PS", "value": str(ps_count)},
            {"name": "DLWS_NUM_WORKER", "value": str(worker_count)},
            {"name": "POD_NAME", "valueFrom": {"fieldRef": {"fieldPath": "metadata.name"}}},
            {"name": "POD_IP", "valueFrom": {"fieldRef": {"fieldPath": "status.podIP"}}},
            ]

    if job.is_host_network:
        envs.append({"name": "DLWS_HOST_NETWORK", "value": "enable"})

    return [{
        "name": "init",
        "imagePullPolicy": "Always",
        "image": job.init_image,
        "command": ["sh", "/dlts-init/init.sh"],
        "env": envs,
        "volumeMounts": [{"mountPath": "/dlts-runtime", "name": "dlts-runtime" }],
        }]

def transform_mount_points(mount_points, plugins):
    result = [{
        "mountPath": mp["containerPath"],
        "name": mp["name"],
        "readOnly": mp.get("readOnly", False),
        } for mp in mount_points if mp.get("enabled")]

    result.extend([{
        "name": bf["name"],
        "mountPath": bf["mountPath"],
        } for bf in plugins.get("blobfuse", []) if bf.get("enabled")])

    return result

def gen_container_envs(job, role):
    ps_count = worker_count = 0
    if job.roles.get("ps") is not None:
        ps_count = job.roles["ps"].task_count
    if job.roles.get("worker") is not None:
        worker_count = job.roles["worker"].task_count
    else:
        worker_count = 1 # regular job, role will be master

    result = [
            {"name": "FAMILY_TOKEN", "value": job.family_token},
            {"name": "DLWS_JOB_ID", "value": str(job.job_id)},
            {"name": "DLWS_NUM_PS", "value": str(ps_count)},
            {"name": "DLWS_NUM_WORKER", "value": str(worker_count)},
            {"name": "POD_NAME",
                "valueFrom": {"fieldRef": {"fieldPath": "metadata.name"}}},
            {"name": "POD_IP",
                "valueFrom": {"fieldRef": {"fieldPath": "status.podIP"}}},
            {"name": "DLWS_GID", "value": str(job.gid)},
            {"name": "DLWS_UID", "value": str(job.uid)},
            {"name": "DLWS_USER_NAME", "value": job.alias},
            {"name": "DLWS_USER_EMAIL", "value": job.email},
            {"name": "DLWS_VC_NAME", "value": job.vc_name},
            {"name": "DLWS_ROLE_NAME", "value": role.name},
            {"name": "DLWS_LAUNCH_CMD", "value": job.user_cmd},
            ]

    if role.resource.gpu_limit < 1:
        result.append({"name": "NVIDIA_VISIBLE_DEVICES", "value": ""})

    if job.is_host_network:
        result.append({"name": "DLWS_HOST_NETWORK", "value": "enable"})

    if job.is_nccl_ib_disabled:
        result.append({"name": "NCCL_IB_DISABLE", "value": "1"})

    result.extend(role.envs)

    return result

def gen_containers(job, role):
    volume_mounts = [
            {"name": "dlts-runtime", "mountPath": "/dlts-runtime"},
            {"name": "dlws-scripts", "mountPath": "/pod/scripts", "readOnly": True},
            {"name": "ssh-volume", "mountPath": "/home/%s/.ssh" % (job.alias)},
            {"name": "id-rsa-volume",
                "mountPath": "/home/%s/.ssh/id_rsa" % (job.alias),
                "readOnly": True},
            {"name": "id-rsa-pub-volume",
                "mountPath": "/home/%s/.ssh/id_rsa.pub" % (job.alias),
                "readOnly": True},
            {"name": "authorized-keys-volume",
                "mountPath": "/home/%s/.ssh/authorized_keys" % (job.alias),
                "readOnly": True},
            {"name": "dshm", "mountPath": "/dev/shm"},
            ]

    if job.dns_policy is None:
        volume_mounts.append({"name": "resolv", "mountPath": "/etc/resolv.conf"})

    volume_mounts.extend(transform_mount_points(job.mount_points, job.plugins))

    spec = [{
        "name": job.job_id,
        "image": role.image,
        "imagePullPolicy": "Always",
        "command": ["bash", "/pod/scripts/bootstrap.sh"],
        "readinessProbe": {
            "exec": {"command": ["ls", "/pod/running/ROLE_READY"]},
            "initialDelaySeconds": 3,
            "periodSeconds": 30
            },
        "securityContext": {
            #"runAsUser": job.uid,
            "privileged": job.is_privileged,
            "capabilities": {"add": ["IPC_LOCK", "SYS_ADMIN"]},
            },
        "resources": gen_resources(role.resource),
        "volumeMounts": volume_mounts,
        "env": gen_container_envs(job, role),
        }]

    return spec

def gen_resources(resource):
    return {
            "requests": {
                "cpu": resource.cpu_req,
                "memory": resource.mem_req,
                },
            "limits": {
                "cpu": resource.cpu_limit,
                "memory": resource.mem_limit,
                "nvidia.com/gpu": resource.gpu_limit,
                }}


def gen_completion_policy(min_failed_task_count, succeeded_task_count):
    result = {}
    if min_failed_task_count is not None:
        result["minFailedTaskCount"] = int(min_failed_task_count)
    if succeeded_task_count is not None:
        result["minSucceededTaskCount"] = int(succeeded_task_count)
    return result


def gen_affinity(job, role):
    if role.resource.gpu_limit == 0 and role.name != "ps":
        return {}
    result = {}

    if role.name == "ps":
        result["podAffinity"] = {
                "requiredDuringSchedulingIgnoredDuringExecution": [{
                    "labelSelector": { # try to put worker & ps in same node
                        "matchExpressions": [
                            {"key": "jobId", "operator": "In", "values": [job.job_id]},
                            {"key": "jobRole", "operator": "In", "values": ["worker"]},
                            ],
                        "topologyKey": "kubernetes.io/hostname",
                        }
                    }]
                }
    else:
        result["podAffinity"] = {
                "preferredDuringSchedulingIgnoredDuringExecution": [
                    # for regular jobs, try to use node already has job running
                    {"weight": 50, "podAffinityTerm": {
                        "labelSelector": {
                            "matchExpressions": [
                                {"key": "type", "operator": "In", "values": ["job"]}],
                            "topologyKey": "kubernetes.io/hostname",
                            }
                        }},
                    # for distributed jobs, try to cluster pod of same job into one region
                    {"weight": 100, "podAffinityTerm": {
                        "labelSelector": {
                            "matchExpressions": [
                                {"key": "jobId", "operator": "In", "values": [job.job_id]}],
                            "topologyKey": "failure-domain.beta.kubernetes.io/region",
                            }
                        }},
                    ]
                }
        result["podAntiAffinity"] = {
                "preferredDuringSchedulingIgnoredDuringExecution": [
                    {"weight": 50, "podAffinityTerm": {
                        "labelSelector": {
                            "matchExpressions": [
                                {"key": "jobId", "operator": "In", "values": [job.job_id]}],
                            "topologyKey": "failure-domain.beta.kubernetes.io/zone",
                            }
                        }}
                    ]
                }

def gen_task_role(job, role):
    node_selector = {"worker": "active"}
    for key, val in job.node_selector.items():
        node_selector[key] = val
    if job.is_fragment_gpu_job:
        node_selector["FragmentGPUJob"] = "active"

    image_pull_secrets = [{"name": "regcred"}]

    image_pull_secrets.extend([{"name": secret["name"]}
        for secret in job.plugins.get("imagePull", []) if secret["enabled"]])

    volumes = [
            {"name": "dlws-scripts", "configMap": {"name": "dlws-scripts"}},
            {"name": "ssh-volume", "emptyDir": {}},
            {"name": "id-rsa-volume",
                "hostPath": {"path": "%s/.ssh/id_rsa" % (job.home_folder_host_path)}},
            {"name": "id-rsa-pub-volume",
                "hostPath": {"path": "%s/.ssh/id_rsa.pub" % (job.home_folder_host_path)}},
            {"name": "authorized-keys-volume",
                "hostPath": {"path": "%s/.ssh/authorized_keys" % (job.home_folder_host_path)}},
            {"name": "dlts-runtime", "emptyDir": {}},
            {"name": "dshm", "emptyDir": {"medium": "Memory"}},
            ]

    if job.dns_policy is None:
        volumes.append({"name": "resolv", "hostPath": {"path": "/etc/resolv.conf"}})

    for mp in job.mount_points:
        if mp["enabled"]:
            volume = {"name": mp["name"]}
            if mp.get("emptydir") is not None:
                volume["emptyDir"] = {}
            else:
                volume["hostPath"] = {"path": mp["hostPath"]}
                if mp.get("type") is not None:
                    volume["hostPath"]["type"] = mp["type"]
            volumes.append(volume)

    for bf in job.plugins.get("blobfuse", []):
        if not bf.get("enabled"):
            continue

        options = {"container": bf["containerName"]}
        if bf.get("root_tmppath") is not None and bf.get("tmppath") is not None:
            options["tmppath"] = "%s/%s/%s/%s" % (bf["root_tmppath"], job.job_id, job.pod_name, bf["tmppath"])
        if bf.get("mountOptions") is not None:
            options["mountoptions"] = bf["mountOptions"]

        volumes.append({
            "name": bf["name"],
            "flexVolume": {
                "driver": "azure/blobfuse",
                "readOnly": False,
                "secretRef": {"name": bf["secreds"]},
                "options": options,
                }
            })

    pod_spec = {
        "nodeSelector": node_selector,
        "restartPolicy": "Never",
        "hostNetwork": job.is_host_network,
        "hostIPC": job.is_host_ipc,
        "imagePullSecrets": image_pull_secrets,
        "affinity": gen_affinity(job, role),
        "initContainers": gen_init_container(job, role),
        "containers": gen_containers(job, role),
        "volumes": volumes,
        }

    if job.dns_policy is not None:
        pod_spec["dnsPolicy"] = job.dns_policy

    labels = {
        "run": job.job_id,
        "jobId": job.job_id,
        "jobRole": role.name,
        "userName": job.alias,
        "vcName": job.vc_name,
        "type": "job",
        "gpu-request": str(role.resource.gpu_limit),
        "role": role.name,
        }

    for k, v in job.labels.items():
        labels[k] = v

    if role.resource.gpu_type is not None:
        labels["gpuType"] = role.resource.gpu_type

    if job.is_preemption_allowed:
        labels["preemptionAllowed"] = str(job.is_preemption_allowed)

    annotations = {}

    for k, v in job.annotations.items():
        annotations[k] = v

    return {
            "name": role.name,
            "taskNumber": role.task_count,
            "frameworkAttemptCompletionPolicy":
            gen_completion_policy(role.min_failed_task_count,
                role.succeeded_task_count)
            , "task": {
                "retryPolicy": {"fancyRetryPolicy": False},
                "pod": {
                    "metadata": {
                        "labels": labels,
                        "annotations": annotations,
                        },
                    "spec": pod_spec,
                    }
                }
            }

def gen_task_roles(job):
    result = []
    for _, role in job.roles.items():
        result.append(gen_task_role(job, role))

    return result

def gen_framework_spec(job):
    return {
            "apiVersion": "frameworkcontroller.microsoft.com/v1",
            "kind": "Framework",
            "metadata": {"name": transform_name(job.job_id)},
            "spec": {
                "executionType": "Start",
                "retryPolicy": {"fancyRetryPolicy": False},
                "taskRoles": gen_task_roles(job)
                }}

def transform_req_limit(req, limit, default_req, default_limit):
    """ return reqest, limit, this ensure that req <= limit """
    if req is None and limit is None:
        return default_req, default_limit
    elif req is None:
        return limit, limit
    elif limit is None:
        return req, req
    else:
        return req, limit

def transform_resource(params, default_cpu_req, default_cpu_limit, default_mem_req, default_mem_limit):
    cpu_req, cpu_limit = transform_req_limit(params.get("cpurequest"), params.get("cpulimit"),
            default_cpu_req, default_cpu_limit)
    mem_req, mem_limit = transform_req_limit(params.get("memoryrequest"), params.get("memorylimit"),
            default_mem_req, default_mem_limit)
    gpu_limit = params.get("gpuLimit", 0)
    gpu_type = params.get("gpuType")

    return Resource(cpu_req, mem_req, cpu_limit, mem_limit, gpu_limit, gpu_type)

def transform_name(name):
    return str(re.sub(r"[-]", "", name.lower()))

def transform_regular_job(params, cluster_config):
    resource = transform_resource(params,
            cluster_config.get("default_cpurequest", "500m"),
            cluster_config.get("default_cpulimit", "500m"),
            cluster_config.get("default_memoryrequest", "2048M"),
            cluster_config.get("default_memorylimit", "2560M"),
            )

    image = params["image"]

    envs = params.get("envs", [])

    roles = {
        "master": Role("master", 1, image, envs, resource, 1, 1),
    }

    labels = params.get("label", {})
    annotations = params.get("annotations", {})

    framework = Framework(
            params["init-container"],
            labels,
            annotations,
            roles,
            params["jobId"],
            params["jobId"], # pod_name here, should fix this before using blobfuse
            params["cmd"],
            params["user"],
            params["user_email"],
            params["gid"],
            params["uid"],
            params["mountpoints"],
            params["plugins"],
            params["familyToken"],
            params["vcName"],
            params.get("dnsPolicy"),
            params.get("nodeSelector", {}),
            params["homeFolderHostpath"],
            params.get("fragmentGpuJob", False),
            params.get("preemptionAllowed", False),
            params.get("hostNetwork", False),
            params.get("hostIPC", False),
            params.get("isPrivileged", False),
            params.get("nccl_ib_disable", False),
            )

    return gen_framework_spec(framework)

def transform_distributed_job(params, cluster_config):
    worker_resource = transform_resource(params,
            cluster_config.get("default_cpurequest", "500m"),
            cluster_config.get("default_cpulimit", "500m"),
            cluster_config.get("default_memoryrequest", "2048M"),
            cluster_config.get("default_memorylimit", "2560M"),
            )
    ps_resource = transform_resource(params,
            cluster_config.get("default_cpurequest", "500m"),
            cluster_config.get("default_cpulimit", "500m"),
            cluster_config.get("default_memoryrequest", "2048M"),
            cluster_config.get("default_memorylimit", "2560M"),
            )
    ps_resource.gpu_limit = 0

    image = params["image"]

    envs = params.get("envs", [])

    roles = {
        "ps": Role("ps", int(params["numps"]), image, envs, ps_resource, 1, 1),
        "worker": Role("worker", int(params["numpsworker"]), image, envs, worker_resource, 1, 1),
    }

    labels = params.get("label", {})
    annotations = params.get("annotations", {})

    framework = Framework(
            params["init-container"],
            labels,
            annotations,
            roles,
            params["jobId"],
            params["jobId"], # pod_name here, should fix this before using blobfuse
            params["cmd"],
            params["user"],
            params["user_email"],
            params["gid"],
            params["uid"],
            params["mountpoints"],
            params["plugins"],
            params["familyToken"],
            params["vcName"],
            params.get("dnsPolicy"),
            params.get("nodeSelector", {}),
            params["homeFolderHostpath"],
            params.get("fragmentGpuJob", False),
            params.get("preemptionAllowed", False),
            params.get("hostNetwork", False),
            params.get("hostIPC", False),
            params.get("isPrivileged", False),
            params.get("nccl_ib_disable", False),
            )

    return gen_framework_spec(framework)

if __name__ == '__main__':
    pass

