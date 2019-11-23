def cpu_format(cpu, ratio=1.0):
    """Convert number of cpu to cpu cycle.

    Args:
        cpu: Number of cpu.
        ratio: The percent that can be used.

    Returns:
        Formatted string of cpu cycle.
    """
    if cpu is None:
        return None
    return "%dm" % int(ratio * cpu * 1000)


def memory_format(memory, ratio=1.0):
    """Convert memory in G to memory requirement.

    Args:
        memory: Memory size in G.
        ratio: The percent that can be used.

    Returns:
        Formatted string of memory size.
    """
    if memory is None:
        return None
    return "%dM" % int(ratio * memory * 1024)


def get_sku_info(sku, config):
    if sku is None:
        return None

    sku_meta = config.get("sku_meta", {})
    sku_info = sku_meta.get(sku, None)
    if sku_info is None:
        return None

    for key in ["cpu", "memory"]:
        if key not in sku_info:
            return None
        if "value" not in sku_info[key]:
            return None

    user_allowed = config.get("user_allowed", {})

    if "cpu" not in user_allowed:
        user_allowed["cpu"] = {}
    if "ratio" not in user_allowed["cpu"]:
        user_allowed["cpu"]["ratio"] = 0.05
    if "memory" not in user_allowed:
        user_allowed["memory"] = {}
    if "ratio" not in user_allowed["memory"]:
        user_allowed["memory"]["ratio"] = 0.1

    for key in ["cpu", "memory"]:
        if "ratio" not in sku_info[key]:
            sku_info[key]["ratio"] = user_allowed[key]["ratio"]

    return sku_info


def enable_cpu_config(params, config):
    # Only works for 0-GPU pod
    if "resourcegpu" not in params or int(params["resourcegpu"]) != 0:
        return params

    # Ignore if cpuworker is not enabled
    enable_cpuworker = config.get("enable_cpuworker", False)
    if enable_cpuworker is False:
        return params

    # Add node selector cpuworker=active
    if "nodeSelector" not in params:
        params["nodeSelector"] = {}
    params["nodeSelector"]["cpuworker"] = "active"

    # Add node selector sku=<sku_value>
    job_training_type = params.get("jobtrainingtype", None)
    default_cpu_sku = config.get("default_cpu_sku")
    if "sku" in params:
        params["nodeSelector"]["sku"] = params["sku"]
    elif default_cpu_sku is not None and job_training_type == "PSDistJob":
        params["nodeSelector"]["sku"] = default_cpu_sku

    # Assign resource requirement based on job type and default configurations
    default_cpu_request = None
    default_cpu_limit = None
    default_memory_request = None
    default_memory_limit = None

    entire_node = job_training_type == "PSDistJob" and params["distRole"] == "worker"

    if entire_node is True:
        sku = params["nodeSelector"].get("sku", None)
        sku_info = get_sku_info(sku=sku, config=config)
        if sku_info is not None:
            default_cpu_request = cpu_format(sku_info["cpu"]["value"],
                                             sku_info["cpu"]["ratio"])
            default_cpu_limit = cpu_format(sku_info["cpu"]["value"],
                                           sku_info["cpu"]["ratio"])
            default_memory_request = memory_format(sku_info["memory"]["value"],
                                                   sku_info["memory"]["ratio"])
            default_memory_limit = memory_format(sku_info["memory"]["value"],
                                                 sku_info["memory"]["ratio"])
    else:
        default_cpu_request = cpu_format(config.get("default_cpurequest"))
        default_cpu_limit = cpu_format(config.get("default_cpulimit"))
        default_memory_request = memory_format(config.get("default_memoryrequest"))
        default_memory_limit = memory_format(config.get("default_memorylimit"))

    if "cpurequest" not in params and default_cpu_request is not None:
        params["cpurequest"] = default_cpu_request
    if "cpulimit" not in params and default_cpu_limit is not None:
        params["cpulimit"] = default_cpu_limit
    if "memoryrequest" not in params and default_memory_request is not None:
        params["memoryrequest"] = default_memory_request
    if "memorylimit" not in params and default_memory_limit is not None:
        params["memorylimit"] = default_memory_limit

    return params
