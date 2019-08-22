import yaml
import os
import logging
import logging.config
import timeit
import functools

from kubernetes import client, config
from kubernetes.client.rest import ApiException
from kubernetes.stream import stream
from kubernetes.stream.ws_client import ERROR_CHANNEL, STDERR_CHANNEL, STDOUT_CHANNEL

from prometheus_client import Histogram

job_deployer_fn_histogram = Histogram("job_deployer_fn_latency_seconds",
        "latency for executing job deployer (seconds)",
        buckets=(.05, .075, .1, .25, .5, .75, 1.0, 2.5, 5.0,
            7.5, 10.0, 12.5, 15.0, 17.5, 20.0, float("inf")),
        labelnames=("fn_name",))

def record(fn):
    @functools.wraps(fn)
    def wrapped(*args, **kwargs):
        start = timeit.default_timer()
        try:
            return fn(*args, **kwargs)
        finally:
            elapsed = timeit.default_timer() - start
            job_deployer_fn_histogram.labels(fn.__name__).observe(elapsed)
    return wrapped


# The config will be loaded from default location.
config.load_kube_config()
k8s_client = client.CoreV1Api()


class JobDeployer:

    def __init__(self):
        self.v1 = k8s_client
        self.namespace = "default"
        self.pretty = "pretty_example"

    @record
    def create_pod(self, body):
        api_response = self.v1.create_namespaced_pod(
            namespace=self.namespace,
            body=body,
            pretty=self.pretty,
        )
        return api_response

    @record
    def delete_pod(self, name, grace_period_seconds=None):
        body = client.V1DeleteOptions()
        body.grace_period_seconds = grace_period_seconds
        api_response = self.v1.delete_namespaced_pod(
            name=name,
            namespace=self.namespace,
            pretty=self.pretty,
            body=body,
            grace_period_seconds=grace_period_seconds,
        )
        return api_response

    @record
    def create_service(self, body):
        api_response = self.v1.create_namespaced_service(
            namespace=self.namespace,
            body=body,
            pretty=self.pretty,
        )
        return api_response

    @record
    def delete_service(self, name):
        api_response = self.v1.delete_namespaced_service(
            name=name,
            namespace=self.namespace,
            pretty=self.pretty,
            body=client.V1DeleteOptions(),
        )
        return api_response

    @record
    def cleanup_pods(self, pod_names, force=False):
        errors = []
        grace_period_seconds = 0 if force else None
        for pod_name in pod_names:
            try:
                self.delete_pod(pod_name, grace_period_seconds)
            except Exception as e:
                if isinstance(e, ApiException) and 404 == e.status:
                    return []
                message = "Delete pod failed: {}".format(pod_name)
                logging.warning(message, exc_info=True)
                errors.append({"message": message, "exception": e})
        return errors

    @record
    def cleanup_services(self, services):
        errors = []
        for service in services:
            assert(isinstance(service, client.V1Service))
            try:
                service_name = service.metadata.name
                self.delete_service(service_name)
            except ApiException as e:
                message = "Delete service failed: {}".format(service_name)
                logging.warning(message, exc_info=True)
                errors.append({"message": message, "exception": e})
        return errors

    @record
    def create_pods(self, pods):
        # TODO instead of delete, we could check update existiong ones. During refactoring, keeping the old way.
        pod_names = [pod["metadata"]["name"] for pod in pods]
        self.cleanup_pods(pod_names)
        created = []
        for pod in pods:
            created_pod = self.create_pod(pod)
            created.append(created_pod)
            logging.info("Create pod succeed: %s" % created_pod.metadata.name)
        return created

    @record
    def get_pods(self, field_selector="", label_selector=""):
        api_response = self.v1.list_namespaced_pod(
            namespace=self.namespace,
            pretty=self.pretty,
            field_selector=field_selector,
            label_selector=label_selector,
        )
        logging.debug("Get pods: {}".format(api_response))
        return api_response.items

    @record
    def get_services_by_label(self, label_selector):
        api_response = self.v1.list_namespaced_service(
            namespace=self.namespace,
            pretty=self.pretty,
            label_selector=label_selector,
        )
        return api_response.items

    @record
    def delete_job(self, job_id, force=False):
        label_selector = "run={}".format(job_id)

        # query pods then delete
        pods = self.get_pods(label_selector=label_selector)
        pod_names = [pod.metadata.name for pod in pods]
        pod_errors = self.cleanup_pods(pod_names, force)

        # query services then delete
        services = self.get_services_by_label(label_selector)
        service_errors = self.cleanup_services(services)

        errors = pod_errors + service_errors
        return errors

    @record
    def pod_exec(self, pod_name, exec_command, timeout=60):
        """work as the command (with timeout): kubectl exec 'pod_name' 'exec_command'"""
        try:
            logging.info("Exec on pod {}: {}".format(pod_name, exec_command))
            client = stream(
                self.v1.connect_get_namespaced_pod_exec,
                name=pod_name,
                namespace=self.namespace,
                command=exec_command,
                stderr=True,
                stdin=False,
                stdout=True,
                tty=False,
                _preload_content=False,
            )
            client.run_forever(timeout=timeout)

            err = yaml.full_load(client.read_channel(ERROR_CHANNEL))
            if err is None:
                return [-1, "Timeout"]

            if err["status"] == "Success":
                status_code = 0
            else:
                logging.debug("Exec on pod {} failed. cmd: {}, err: {}.".format(pod_name, exec_command, err))
                status_code = int(err["details"]["causes"][0]["message"])
            output = client.read_all()
            logging.info("Exec on pod {}, status: {}, cmd: {}, output: {}".format(pod_name, status_code, exec_command, output))
            return [status_code, output]
        except ApiException as err:
            logging.error("Exec on pod {} error. cmd: {}, err: {}.".format(pod_name, exec_command, err), exc_info=True)
            return [-1, err.message]
