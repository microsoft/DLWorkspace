#!/usr/bin/env python3


def enable_cpu_config(pod, config):
    # TODO: Refactor this function with JobRestAPIUtils.populate_cpu_resource
    # Ignore if cpuworker is not enabled
    enable_cpuworker = config.get("enable_cpuworker", False)
    if enable_cpuworker is False:
        return pod

    # Only works for 0-GPU job
    if "resourcegpu" not in pod or int(pod["resourcegpu"]) != 0:
        return pod

    dist_role = pod.get("distRole", None)

    # Add node selector cpuworker=active
    if "nodeSelector" not in pod:
        pod["nodeSelector"] = {}
    pod["nodeSelector"]["cpuworker"] = "active"

    # Use default resouce request
    if dist_role == "ps":
        pod.pop("cpurequest", None)
        pod.pop("cpulimit", None)
        pod.pop("memoryrequest", None)
        pod.pop("memorylimit", None)

    return pod
