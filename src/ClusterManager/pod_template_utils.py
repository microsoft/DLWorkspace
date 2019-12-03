#!/usr/bin/python
def cpu_format(cpu, ratio=1.0):
    """Convert number of cpu to cpu cycle.

    Args:
        cpu: Number of cpu.
        ratio: The percent that can be used.

    Returns:
        Formatted string of cpu cycle if cpu is valid, None otherwise.
    """
    try:
        cpu = float(cpu)
    except:
        return None
    else:
        return "%dm" % int(ratio * cpu * 1000)


def mem_format(memory, ratio=1.0):
    """Convert memory in G to memory requirement.

    Args:
        memory: Memory size in G.
        ratio: The percent that can be used.

    Returns:
        Formatted string of memory size if memory is valid, None otherwise.
    """
    try:
        memory = float(memory)
    except:
        return None
    else:
        return "%dM" % int(ratio * memory * 1024)


def get_sku_info(sku, config):
    """Returns a sku info dictionary for sku.

    Args:
        sku: String specifying machine's SKU.
        config: Configuration containing sku_meta.

    Returns:
        A dictionary containing sku info for the given machine sku, including
        - cpu
        - cpu usable ratio
        - memory
        - memory usable ratio
        if sku and sku_info in config["sku_meta"] are valid, None otherwise.
    """
    # Ignore invalid sku and sku_info.
    if sku is None:
        return None

    sku_meta = config.get("sku_meta", {})
    sku_info = sku_meta.get(sku, None)
    if sku_info is None:
        return None

    for key in ["cpu", "memory"]:
        if key not in sku_info:
            return None

    # Default sku_info must contain ratio info.
    # Assign 0.8 as default if default values are not defined.
    default_sku_info = sku_meta.get("default", {})

    for key in ["cpu_ratio", "memory_ratio"]:
        if key not in default_sku_info:
            default_sku_info[key] = 0.8

    # Override ratios in sku_info with default values if absent.
    for key in ["cpu_ratio", "memory_ratio"]:
        if key not in sku_info:
            sku_info[key] = default_sku_info[key]

    return sku_info


def enable_cpu_config(pod, config):
    """Add node selector and cpu, memory requirement info for CPU pod.

    Args:
        pod: Pod configuration directory to for starting a Kubernetes pod.
        config: Configuration containing cluster-wide info.

    Returns:
        Potentially modified pod.
    """
    # Ignore if cpuworker is not enabled
    enable_cpuworker = config.get("enable_cpuworker", False)
    if enable_cpuworker is False:
        return pod

    # Only works for 0-GPU job
    if "resourcegpu" not in pod or int(pod["resourcegpu"]) != 0:
        return pod

    # When cpuworker is enabled, CPU job should have gpuType=None
    if "nodeSelector" not in pod:
        pod["nodeSelector"] = {}
    pod["nodeSelector"]["gpuType"] = "None"

    job_training_type = pod.get("jobtrainingtype", None)
    dist_role = pod.get("distRole", None)

    # No special config for ps pod. It is always co-located with a worker
    if dist_role == "ps":
        return pod

    # Add node selector cpuworker=active
    pod["nodeSelector"]["cpuworker"] = "active"

    # Add node selector sku=<sku_value>
    default_cpu_sku = config.get("default_cpu_sku", None)
    if "sku" in pod:
        pod["nodeSelector"]["sku"] = pod["sku"]
    elif default_cpu_sku is not None and job_training_type == "PSDistJob":
        pod["nodeSelector"]["sku"] = default_cpu_sku

    # Assign resource requirement based on job type and default configuration.
    # Pod requiring a full node requires occupying cpu and memory as much as
    # possible on a node. We attempt to achieve this by using cluster-wide
    # cpu usable ratio multiplied into cpu count, and memory usable ratio
    # multiplied into memory size.
    default_cpu_request = None
    default_cpu_limit = None
    default_mem_request = None
    default_mem_limit = None

    if job_training_type == "PSDistJob" and dist_role == "worker":
        full_node = True
    else:
        full_node = False

    if full_node is True:
        sku = pod["nodeSelector"].get("sku", None)
        sku_info = get_sku_info(sku=sku, config=config)
        if sku_info is not None:
            # Do not restrict the limit for full node worker
            default_cpu_request = cpu_format(sku_info["cpu"],
                                             sku_info["cpu_ratio"])
            default_mem_request = mem_format(sku_info["memory"],
                                             sku_info["memory_ratio"])
    else:
        default_cpu_request = cpu_format(config.get("default_cpurequest"))
        default_cpu_limit = cpu_format(config.get("default_cpulimit"))
        default_mem_request = mem_format(config.get("default_memoryrequest"))
        default_mem_limit = mem_format(config.get("default_memorylimit"))

    if "cpurequest" not in pod and default_cpu_request is not None:
        pod["cpurequest"] = default_cpu_request
    if "cpulimit" not in pod and default_cpu_limit is not None:
        pod["cpulimit"] = default_cpu_limit
    if "memoryrequest" not in pod and default_mem_request is not None:
        pod["memoryrequest"] = default_mem_request
    if "memorylimit" not in pod and default_mem_limit is not None:
        pod["memorylimit"] = default_mem_limit

    return pod
