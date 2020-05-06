#!/usr/bin/env python3

import logging
import re

logger = logging.getLogger(__name__)


class Resource(object):
    def __init__(self, cpu_req, mem_req, cpu_limit, mem_limit, gpu_limit,
                 gpu_type):
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
    def __init__(self, init_image, labels, annotations, roles, job_id, pod_name,
                 user_cmd, alias, email, gid, uid, mount_points, plugins,
                 family_token, vc_name, dns_policy, node_selector,
                 ssh_private_key, ssh_public_keys, priority_class,
                 is_preemption_allowed, is_host_network, is_host_ipc,
                 is_privileged, is_debug):
        self.init_image = init_image # str, maybe None
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
        self.ssh_private_key = ssh_private_key # str
        self.ssh_public_keys = ssh_public_keys # list of str
        self.priority_class = priority_class # str
        self.is_preemption_allowed = is_preemption_allowed # bool
        self.is_host_network = is_host_network # bool
        self.is_host_ipc = is_host_ipc # bool
        self.is_privileged = is_privileged # bool
        self.is_debug = is_debug # bool


def gen_init_container(job, role):
    ps_count = worker_count = 0
    if job.roles.get("ps") is not None:
        ps_count = job.roles["ps"].task_count
    if job.roles.get("worker") is not None:
        worker_count = job.roles["worker"].task_count
    else:
        worker_count = 1 # regular job, role will be master

    envs = [
        {
            "name": "DLTS_JOB_ID",
            "value": str(job.job_id)
        },
        {
            "name": "DLTS_NUM_PS",
            "value": str(ps_count)
        },
        {
            "name": "DLTS_NUM_WORKER",
            "value": str(worker_count)
        },
        {
            "name": "POD_NAME",
            "valueFrom": {
                "fieldRef": {
                    "fieldPath": "metadata.name"
                }
            }
        },
        {
            "name": "POD_IP",
            "valueFrom": {
                "fieldRef": {
                    "fieldPath": "status.podIP"
                }
            }
        },
    ]

    if job.is_debug:
        envs.append({"name": "LOGGING_LEVEL", "value": "DEBUG"})
    else:
        envs.append({"name": "LOGGING_LEVEL", "value": "INFO"})

    if job.is_host_network:
        envs.append({"name": "DLTS_HOST_NETWORK", "value": "enable"})

    return [{
        "name":
            "init",
        "imagePullPolicy":
            "Always",
        "image":
            job.init_image,
        "command": ["sh", "/dlts-init/init.sh"],
        "env":
            envs,
        "volumeMounts": [{
            "mountPath": "/dlts-runtime",
            "name": "dlts-runtime"
        }],
    }]


def transform_mount_points(mount_points):
    result = []
    for mp in mount_points:
        if mp.get("enabled") is not True:
            continue

        res = {
            "mountPath": mp["mountPath"],
            "name": mp["name"],
        }
        sub_path = mp.get("subPath")
        if sub_path is not None:
            res["subPath"] = sub_path
        read_only = mp.get("readOnly")
        if read_only is not None:
            res["readOnly"] = read_only

        result.append(res)
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
        {
            "name": "FAMILY_TOKEN",
            "value": job.family_token
        },
        {
            "name": "DLWS_JOB_ID",
            "value": str(job.job_id)
        },
        {
            "name": "DLTS_JOB_ID",
            "value": str(job.job_id)
        },
        {
            "name": "DLWS_NUM_PS",
            "value": str(ps_count)
        },
        {
            "name": "DLTS_NUM_PS",
            "value": str(ps_count)
        },
        {
            "name": "DLWS_NUM_WORKER",
            "value": str(worker_count)
        },
        {
            "name": "DLTS_NUM_WORKER",
            "value": str(worker_count)
        },
        {
            "name": "POD_NAME",
            "valueFrom": {
                "fieldRef": {
                    "fieldPath": "metadata.name"
                }
            }
        },
        {
            "name": "POD_IP",
            "valueFrom": {
                "fieldRef": {
                    "fieldPath": "status.podIP"
                }
            }
        },
        {
            "name": "DLWS_GID",
            "value": str(job.gid)
        },
        {
            "name": "DLTS_GID",
            "value": str(job.gid)
        },
        {
            "name": "DLWS_UID",
            "value": str(job.uid)
        },
        {
            "name": "DLTS_UID",
            "value": str(job.uid)
        },
        {
            "name": "DLWS_USER_NAME",
            "value": job.alias
        },
        {
            "name": "DLTS_USER_NAME",
            "value": job.alias
        },
        {
            "name": "DLWS_USER_EMAIL",
            "value": job.email
        },
        {
            "name": "DLTS_USER_EMAIL",
            "value": job.email
        },
        {
            "name": "DLWS_VC_NAME",
            "value": job.vc_name
        },
        {
            "name": "DLTS_VC_NAME",
            "value": job.vc_name
        },
        {
            "name": "DLWS_ROLE_NAME",
            "value": role.name
        },
        {
            "name": "DLTS_ROLE_NAME",
            "value": role.name
        },
        {
            "name": "DLWS_LAUNCH_CMD",
            "value": job.user_cmd
        },
        {
            "name": "DLTS_LAUNCH_CMD",
            "value": job.user_cmd
        },
        {
            "name": "DLTS_SSH_PRIVATE_KEY",
            "value": job.ssh_private_key
        },
    ]

    if role.resource.gpu_limit < 1:
        result.append({"name": "NVIDIA_VISIBLE_DEVICES", "value": ""})

    if job.is_host_network:
        result.append({"name": "DLWS_HOST_NETWORK", "value": "enable"})
        result.append({"name": "DLTS_HOST_NETWORK", "value": "enable"})

    if job.is_preemption_allowed:
        result.append({"name": "DLTS_PREEMPTIBLE", "value": "true"})
    else:
        result.append({"name": "DLTS_PREEMPTIBLE", "value": "false"})

    for i, key_value in enumerate(job.ssh_public_keys):
        result.append({
            "name": "DLTS_PUBLIC_SSH_KEY_%d" % i,
            "value": key_value
        })

    result.extend(role.envs)

    return result


def gen_containers(job, role):
    volume_mounts = [
        {
            "name": "dlts-runtime",
            "mountPath": "/dlts-runtime"
        },
        {
            "name": "dlws-scripts",
            "mountPath": "/dlws-scripts",
            "readOnly": True
        },
        {
            "name": "ssh-volume",
            "mountPath": "/home/%s/.ssh" % (job.alias)
        },
        {
            "name": "dshm",
            "mountPath": "/dev/shm"
        },
    ]

    if job.dns_policy is None:
        volume_mounts.append({
            "name": "resolv",
            "mountPath": "/etc/resolv.conf"
        })

    volume_mounts.extend(transform_mount_points(job.mount_points))
    logger.debug("volume_mounts: %s", volume_mounts)

    if job.init_image is None:
        # This act like init_image for inference jobs, because inference jobs do not need to setup sshd
        cmd = [
            "sh", "-c", """
            printenv DLWS_LAUNCH_CMD > /job_command.sh
            chmod +x /job_command.sh
            mkdir -p /dlts-runtime/status
            touch /dlts-runtime/status/READY
            mkdir /dlts-runtime/env
            bash /dlws-scripts/init_user.sh
            runuser -s /bin/bash -l ${DLTS_USER_NAME} -c /job_command.sh
            """
        ]
    else:
        cmd = ["bash", "/dlws-scripts/bootstrap.sh"]

    spec = [{
        "name": job.job_id,
        "image": role.image,
        "imagePullPolicy": "Always",
        "command": cmd,
        "readinessProbe": {
            "exec": {
                "command": ["ls", "/dlts-runtime/status/READY"]
            },
            "initialDelaySeconds": 3,
            "periodSeconds": 10
        },
        "securityContext": {
            "runAsUser": 0,
            "privileged": job.is_privileged,
            "capabilities": {
                "add": ["IPC_LOCK", "SYS_ADMIN"]
            },
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
        }
    }


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
                        },
                    "topologyKey": "kubernetes.io/hostname",
                    }],
                }
    else:
        result["podAffinity"] = {
            "preferredDuringSchedulingIgnoredDuringExecution": [
                # for regular jobs, try to use node already has job running
                {
                    "weight": 50,
                    "podAffinityTerm": {
                        "labelSelector": {
                            "matchExpressions": [{
                                "key": "type",
                                "operator": "In",
                                "values": ["job"]
                            }],
                        },
                        "topologyKey": "kubernetes.io/hostname",
                    }
                },
                # for distributed jobs, try to cluster pod of same job into one region
                {
                    "weight": 100,
                    "podAffinityTerm": {
                        "labelSelector": {
                            "matchExpressions": [{
                                "key": "jobId",
                                "operator": "In",
                                "values": [job.job_id]
                            }],
                        },
                        "topologyKey":
                            "failure-domain.beta.kubernetes.io/region",
                    }
                },
            ]
        }
        result["podAntiAffinity"] = {
            "preferredDuringSchedulingIgnoredDuringExecution": [{
                "weight": 50,
                "podAffinityTerm": {
                    "labelSelector": {
                        "matchExpressions": [{
                            "key": "jobId",
                            "operator": "In",
                            "values": [job.job_id]
                        }],
                    },
                    "topologyKey": "failure-domain.beta.kubernetes.io/zone",
                }
            }]
        }
    return result


def gen_task_role(job, role):
    node_selector = {"worker": "active"}
    for key, val in job.node_selector.items():
        node_selector[key] = val

    image_pull_secrets = [{"name": "regcred"}]

    image_pull_secrets.extend([{
        "name": secret["name"]
    } for secret in job.plugins.get("imagePull", []) if secret["enabled"]])

    volumes = [
        {
            "name": "dlws-scripts",
            "configMap": {
                "name": "dlws-scripts"
            }
        },
        {
            "name": "ssh-volume",
            "emptyDir": {}
        },
        {
            "name": "dlts-runtime",
            "emptyDir": {}
        },
        {
            "name": "dshm",
            "emptyDir": {
                "medium": "Memory"
            }
        },
    ]

    if job.dns_policy is None:
        volumes.append({
            "name": "resolv",
            "hostPath": {
                "path": "/etc/resolv.conf"
            }
        })

    for mp in job.mount_points:
        if not mp.get("enabled"):
            continue

        volume = {"name": mp["name"]}
        if mp.get("emptydir") is not None:
            volume["emptyDir"] = {}
        elif mp.get("mountType") == "hostPath":
            volume["hostPath"] = {"path": mp["hostPath"]}
            if mp.get("type") is not None:
                volume["hostPath"]["type"] = mp["type"]
        elif mp.get("mountType") == "nfs":
            volume["nfs"] = {
                "server": mp["server"],
                "path": mp["path"],
            }
        elif mp.get("mountType") == "blobfuse":
            options = {"container": mp["containerName"]}
            if mp.get("rootTmppath") is not None and \
                    mp.get("tmppath") is not None:
                options["tmppath"] = "%s/%s/%s/%s" % (
                    mp["rootTmppath"], job.job_id, job.pod_name, mp["tmppath"])
            if mp.get("mountOptions") is not None:
                options["mountoptions"] = mp["mountOptions"]
            volume["flexVolume"] = {
                "driver": "azure/blobfuse",
                "readOnly": False,
                "secretRef": {
                    "name": mp["secreds"]
                },
                "options": options,
            }
        else:
            logger.warning("Unrecognized mountpoint %s", mp)
            continue
        volumes.append(volume)

    logger.info("volumes: %s", volumes)

    pod_spec = {
        "nodeSelector": node_selector,
        "restartPolicy": "Never",
        "hostNetwork": job.is_host_network,
        "hostIPC": job.is_host_ipc,
        "imagePullSecrets": image_pull_secrets,
        "affinity": gen_affinity(job, role),
        "containers": gen_containers(job, role),
        "volumes": volumes,
    }
    if job.priority_class is not None:
        pod_spec["priorityClassName"] = job.priority_class

    if job.init_image is not None:
        pod_spec["initContainers"] = gen_init_container(job, role)

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
        "name":
            role.name,
        "taskNumber":
            role.task_count,
        "frameworkAttemptCompletionPolicy":
            gen_completion_policy(role.min_failed_task_count,
                                  role.succeeded_task_count),
        "task": {
            "retryPolicy": {
                "fancyRetryPolicy": False,
                "maxRetryCount": 0,
            },
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
        "metadata": {
            "name": transform_name(job.job_id)
        },
        "spec": {
            "executionType": "Start",
            "retryPolicy": {
                "fancyRetryPolicy": True,
                "maxRetryCount": 3,
            },
            "taskRoles": gen_task_roles(job)
        }
    }


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


def transform_resource(params, default_cpu_req, default_cpu_limit,
                       default_mem_req, default_mem_limit):
    cpu_req, cpu_limit = transform_req_limit(params.get("cpurequest"),
                                             params.get("cpulimit"),
                                             default_cpu_req, default_cpu_limit)
    mem_req, mem_limit = transform_req_limit(params.get("memoryrequest"),
                                             params.get("memorylimit"),
                                             default_mem_req, default_mem_limit)
    gpu_limit = params.get("gpuLimit", 0)
    gpu_type = params.get("gpuType")

    return Resource(cpu_req, mem_req, cpu_limit, mem_limit, gpu_limit, gpu_type)


def transform_name(name):
    return str(re.sub(r"[-]", "", name.lower()))


def transform_regular_job(params, cluster_config):
    resource = transform_resource(
        params,
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
    if cluster_config["is_support_pod_priority"]:
        priority_class = "job-priority"
    else:
        priority_class = None

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
        params.get("private_key", ""),
        params.get("ssh_public_keys", []),
        priority_class,
        params.get("preemptionAllowed", False),
        params.get("hostNetwork", False),
        params.get("hostIPC", False),
        params.get("isPrivileged", False),
        params.get("debug", False),
    )

    return gen_framework_spec(framework)


def transform_distributed_job(params, cluster_config):
    worker_resource = transform_resource(
        params,
        cluster_config.get("default_cpurequest", "500m"),
        cluster_config.get("default_cpulimit", "500m"),
        cluster_config.get("default_memoryrequest", "2048M"),
        cluster_config.get("default_memorylimit", "2560M"),
    )
    ps_resource = transform_resource(
        params,
        cluster_config.get("default_cpurequest", "500m"),
        cluster_config.get("default_cpulimit", "500m"),
        cluster_config.get("default_memoryrequest", "2048M"),
        cluster_config.get("default_memorylimit", "2560M"),
    )
    ps_resource.gpu_limit = 0
    # To be backward compatible
    ps_resource.cpu_req = "1000m"
    ps_resource.cpu_limit = "1000m"
    ps_resource.mem_req = "0Mi"
    ps_resource.mem_limit = "2048Mi"

    image = params["image"]

    envs = params.get("envs", [])

    roles = {
        "ps":
            Role("ps", int(params["numps"]), image, envs, ps_resource, 1, 1),
        "worker":
            Role("worker", int(params["numpsworker"]), image, envs,
                 worker_resource, 1, 1),
    }

    labels = params.get("label", {})
    annotations = params.get("annotations", {})
    if cluster_config["is_support_pod_priority"]:
        priority_class = "job-priority"
    else:
        priority_class = None

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
        params.get("private_key", ""),
        params.get("ssh_public_keys", []),
        priority_class,
        params.get("preemptionAllowed", False),
        params.get("hostNetwork", False),
        params.get("hostIPC", False),
        params.get("isPrivileged", False),
        params.get("debug", False),
    )

    return gen_framework_spec(framework)


def transform_inference_job(params, cluster_config):
    master_resource = transform_resource(
        params,
        cluster_config.get("default_cpurequest", "500m"),
        cluster_config.get("default_cpulimit", "500m"),
        cluster_config.get("default_memoryrequest", "2048M"),
        cluster_config.get("default_memorylimit", "2560M"),
    )
    worker_resource = transform_resource(
        params,
        cluster_config.get("default_cpurequest", "500m"),
        cluster_config.get("default_cpulimit", "500m"),
        cluster_config.get("default_memoryrequest", "2048M"),
        cluster_config.get("default_memorylimit", "2560M"),
    )
    master_resource.gpu_limit = 0
    worker_resource.gpu_limit = 1

    image = params["image"]

    envs = params.get("envs", [])

    roles = {
        "master":
            Role("master", 1, image, envs, master_resource, 1, 1),
        "worker":
            Role("worker", int(params["resourcegpu"]), image, envs,
                 worker_resource, 1, 1),
    }

    labels = params.get("label", {})
    annotations = params.get("annotations", {})

    if cluster_config["is_support_pod_priority"]:
        priority_class = "inference-job-priority"
    else:
        priority_class = None

    framework = Framework(
        None, # init container
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
        params.get("private_key", ""),
        params.get("ssh_public_keys", []),
        priority_class,
        params.get("preemptionAllowed", False),
        params.get("hostNetwork", False),
        params.get("hostIPC", False),
        params.get("isPrivileged", False),
        params.get("debug", False),
    )

    return gen_framework_spec(framework)


def transform_job(job_type, params, cluster_config):
    if job_type == "RegularJob":
        return transform_regular_job(params, cluster_config)
    elif job_type == "PSDistJob":
        return transform_distributed_job(params, cluster_config)
    elif job_type == "InferenceJob":
        return transform_inference_job(params, cluster_config)
    else:
        logger.error("Unknown job type %s, params is %s", job_type, params)
        raise RuntimeError("Unknown job type %s" % (job_type))


if __name__ == '__main__':
    pass
