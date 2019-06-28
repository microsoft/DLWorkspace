import json
from jinja2 import Template


class PodTemplate():
    def __init__(self, template, enable_custom_scheduler):
        self.template = template
        self.enable_custom_scheduler = enable_custom_scheduler

    def generate_pod_yaml(self, pod):
        assert(isinstance(self.template, Template))
        if self.enable_custom_scheduler:
            if "useGPUTopology" in pod and pod["useGPUTopology"]:
                gpu_topology_flag = 1
            else:
                # for cases when desired topology is explictly given or not desired
                gpu_topology_flag = 0
            pod_name = pod["podName"]
            request_gpu = int(pod["resourcegpu"])

            podInfo = {
                "podname": pod_name,
                "requests": {
                    "alpha.gpu/gpu-generate-topology": gpu_topology_flag
                },
                "runningcontainer": {
                    pod_name: {
                        "requests": {"alpha.gpu/numgpu": request_gpu}
                    },
                },
            }

            if "annotations" not in pod:
                pod["annotations"] = {}
            pod["annotations"]["pod.alpha/DeviceInformation"] = "'" + json.dumps(podInfo) + "'"
            # TODO it's not safe to update pod["resourcegpu"]
            pod["resourcegpu"] = 0  # gpu requests specified through annotation

        if "nodeSelector" not in pod:
            pod["nodeSelector"] = {}
        if "gpuType" in pod:
            pod["nodeSelector"]["gpuType"] = pod["gpuType"]

        # template = job_object.get_template()
        return self.template.render(job=pod)
