import unittest
import kubernetes
import yaml
from kubernetes.client.rest import ApiException

from job_deployer import JobDeployer


class TestJobDeployer(unittest.TestCase):

    def create_job_deployer(self):
        job_deployer = JobDeployer()
        self.assertIsNotNone(job_deployer)
        return job_deployer

    def test_create_pod(self):
        job_deployer = self.create_job_deployer()
        raw_yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: test-pod
spec:
  containers:
  - name: busybox
    image: busybox
    args:
    - sleep
    - "1000000"
    """
        body = yaml.load(raw_yaml)

        # with self.assertRaises(ApiException):
        job_deployer.create_pod(body)

    def test_delete_pod(self):
        job_deployer = self.create_job_deployer()

        job_deployer.delete_pod("test-pod")

    def test_cleanup_pods(self):
        job_deployer = self.create_job_deployer()

        pods = [
            {"metadata": {"name": "pod-1"}},
            {"metadata": {"name": "pod-2"}},
        ]

        job_deployer.cleanup_pods(pods)
