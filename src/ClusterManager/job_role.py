from job_deployer import JobDeployer


class JobRole:
    # MARK_CONTAINER_READY_FILE = "/dlws/CONTAINER_READY"
    # MARK_WORKER_READY_FILE = "/dlws/WORKER_READY"
    MARK_JOB_READY_FILE = "/dlws/JOB_READY"

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
        Return role status.
        It's slightly different from pod phase, when pod is running:
            CONTAINER_READY -> WORKER_READY -> JOB_READY (then the job finally in "Running" status.)
        """
        # pod-phase: https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#pod-phase
        deployer = JobDeployer()
        pods = deployer.get_pods(field_selector="metadata.name={}".format(self.pod_name))
        if(len(pods) < 1):
            return "NotFound"

        assert(len(pods) == 1)
        pod = pods[0]
        phase = pod.status.phase

        # !!! Pod is runing, doesn't mean "Role" is ready and running.
        if(phase == "Running"):
            if not self.isJobReady():
                return "Pending"

        # TODO handle exit status

        return phase

    def isFileExisting(self, file):
        deployer = JobDeployer()
        status_code, _ = deployer.pod_exec(self.pod_name, ["/bin/sh", "-c", "ls -lrt {}".format(file)])
        return status_code == 0

    # def isUserReady(self):
    #     return self.isFileExisting(JobRole.MARK_USER_READY_FILE)

    # def isWorkerReady(self):
    #     return self.isFileExisting(JobRole.MARK_WORKER_READY_FILE)

    def isJobReady(self):
        # only mark job ready on the "ps" or "master" pod
        if(self.role_name not in ["ps", "master"]):
            return False
        return self.isFileExisting(JobRole.MARK_JOB_READY_FILE)
