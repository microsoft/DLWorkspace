import unittest
import kubernetes
import yaml
import string
import random
import time
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

    def create_pod(self, pod_name):
        job_deployer = self.create_job_deployer()
        raw_yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: {}
spec:
  containers:
  - name: busybox
    image: busybox
    args:
    - sleep
    - "1000000"
    """.format(pod_name)
        body = yaml.full_load(raw_yaml)

        # with self.assertRaises(ApiException):
        job_deployer.create_pod(body)

    def test_delete_pod(self):
        pod_name = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(16))
        self.create_pod(pod_name)

        job_deployer = self.create_job_deployer()

        job_deployer.delete_pod(pod_name)

    def test_cleanup_pods(self):
        job_deployer = self.create_job_deployer()
        pod_names = ["pod-1", "pod-2"]

        job_deployer.cleanup_pods(pod_names)

    def test_get_pod_by_label(self):
        job_deployer = self.create_job_deployer()
        label_selector = "run=some_job_id"

        pods = job_deployer.get_pods(label_selector=label_selector)

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

        pod_name = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(16))
        self.create_pod(pod_name)
        time.sleep(3)

        exec_command = [
            '/bin/sh',
            '-c',
            'echo This message goes to stderr >&2 && echo This message goes to stdout'
        ]

        status_code, ouput = job_deployer.pod_exec(pod_name, exec_command)
        self.assertEqual(0, status_code)

        bad_command = [
            '/bin/sh',
            '-c',
            'echo This message goes to stderr >&2 && xecho This message goes to stdout; sleep 3; exit 8'
        ]
        status_code, ouput = job_deployer.pod_exec(pod_name, bad_command)
        self.assertEqual(8, status_code)

        bad_command = [
            '/bin/sh',
            '-c',
            'echo This message goes to stderr >&2 && xecho This message goes to stdout; sleep 3; exit 8'
        ]
        status_code, ouput = job_deployer.pod_exec(pod_name, bad_command, 1)
        self.assertEqual(-1, status_code)

        job_deployer.delete_pod(pod_name)
