import unittest
import kubernetes
import yaml
from kubernetes.client.rest import ApiException

from job_deployer import JobDeployer

import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)


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
        body = yaml.full_load(raw_yaml)

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

    def test_get_pod_by_label(self):
        job_deployer = self.create_job_deployer()
        label_selector = "run=some_job_id"

        pods = job_deployer.get_pods_by_label(label_selector)

        self.assertEqual(0, len(pods))

    def test_get_services_by_label(self):
        job_deployer = self.create_job_deployer()
        label_selector = "run=some_job_id"

        services = job_deployer.get_services_by_label(label_selector)

        self.assertEqual(0, len(services))

    def test_create_endpoint(self):
        job_deployer = self.create_job_deployer()
        raw_yaml = """
apiVersion: v1
kind: Service
metadata:
  name: test-service
spec:
  selector:
    app: MyApp
  ports:
  - protocol: TCP
    port: 80
    targetPort: 9376
    """
        body = yaml.full_load(raw_yaml)

        # with self.assertRaises(ApiException):
        job_deployer.create_service(body)

    def test_delete_service(self):
        job_deployer = self.create_job_deployer()

        job_deployer.delete_service("test-service")

    def test_pod_exec(self):
        job_deployer = self.create_job_deployer()
        exec_command = [
            '/bin/sh',
            '-c',
            'echo This message goes to stderr >&2 && echo This message goes to stdout'
        ]

        status_code, ouput = job_deployer.pod_exec("test-pod", exec_command)
        self.assertEqual(0, status_code)

        bad_command = [
            '/bin/sh',
            '-c',
            'echo This message goes to stderr >&2 && xecho This message goes to stdout; exit 8'
        ]
        status_code, ouput = job_deployer.pod_exec("test-pod", bad_command)
        self.assertEqual(8, status_code)
