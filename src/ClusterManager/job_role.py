import logging
import logging.config
from job_deployer import JobDeployer


class JobRole:
    MARK_ROLE_READY_FILE = "/pod/running/ROLE_READY"

    @staticmethod
    def get_job_roles(job_id):
        deployer = JobDeployer()
        pods = deployer.get_pods(label_selector="run={}".format(job_id))

        job_roles = []
        for pod in pods:
            pod_name = pod.metadata.name
            if "distRole" in pod.metadata.labels:
                role = pod.metadata.labels["distRole"]
            else:
                role = "master"
            job_role = JobRole(role, pod_name)
            job_roles.append(job_role)
        return job_roles

    def __init__(self, role_name, pod_name):
        self.role_name = role_name
        self.pod_name = pod_name

    def status(self):
        """
        Return role status in ["NotFound", "Pending", "Running", "Succeeded", "Failed", "Unknown"]
        It's slightly different from pod phase, when pod is running:
            CONTAINER_READY -> WORKER_READY -> JOB_READY (then the job finally in "Running" status.)
        """
        # pod-phase: https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#pod-phase
        # node condition: https://kubernetes.io/docs/concepts/architecture/nodes/#condition
        deployer = JobDeployer()
        pods = deployer.get_pods(field_selector="metadata.name={}".format(self.pod_name))
        logging.debug("Pods: {}".format(pods))
        if(len(pods) < 1):
            return "NotFound"

        assert(len(pods) == 1)
        self.pod = pods[0]
        phase = self.pod.status.phase

        # !!! Pod is running, doesn't mean "Role" is ready and running.
        if(phase == "Running"):
            # Found that phase won't turn into "Unkonwn" even when we get 'unknown' from kubectl
            if self.pod.status.reason == "NodeLost":
                return "Unknown"

            # Check if the user command had been ran.
            if not self.isRoleReady():
                return "Pending"

        return phase

    # TODO should call after status(), or the self.pod would be None
    def pod_details(self):
        return self.pod

    def isFileExisting(self, file):
        deployer = JobDeployer()
        status_code, _ = deployer.pod_exec(self.pod_name, ["/bin/sh", "-c", "ls -lrt {}".format(file)])
        return status_code == 0

    def isRoleReady(self):
        return self.isFileExisting(JobRole.MARK_ROLE_READY_FILE)
