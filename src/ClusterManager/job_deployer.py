import yaml
import os
import logging
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from kubernetes.stream import stream
from kubernetes.stream.ws_client import ERROR_CHANNEL, STDERR_CHANNEL, STDOUT_CHANNEL


class JobDeployer:

    def __init__(self):
        # The config will be loaded from default location.
        config.load_kube_config()
        self.v1 = client.CoreV1Api()
        self.namespace = "default"
        self.pretty = "pretty_example"

    def create_pod(self, body, dry_run=None):
        api_response = self.v1.create_namespaced_pod(
            namespace=self.namespace,
            body=body,
            pretty=self.pretty,
            dry_run=dry_run,
        )
        return api_response

    def delete_pod(self, name, dry_run=None):
        api_response = self.v1.delete_namespaced_pod(
            name=name,
            namespace=self.namespace,
            pretty=self.pretty,
            body=client.V1DeleteOptions(),
            dry_run=dry_run,
        )
        return api_response

    def create_service(self, body, dry_run=None):
        api_response = self.v1.create_namespaced_service(
            namespace=self.namespace,
            body=body,
            pretty=self.pretty,
            dry_run=dry_run,
        )
        return api_response

    def delete_service(self, name, dry_run=None):
        api_response = self.v1.delete_namespaced_service(
            name=name,
            namespace=self.namespace,
            pretty=self.pretty,
            body=client.V1DeleteOptions(),
            dry_run=dry_run,
        )
        return api_response

    def cleanup_pods(self, pod_names):
        errors = []
        for pod_name in pod_names:
            try:
                self.delete_pod(pod_name)
            except Exception as e:
                if isinstance(e, ApiException) and 404 == e.status:
                    return []
                message = "Delete pod failed: {}".format(pod_name)
                logging.warning(message, exc_info=True)
                errors.append({"message": message, "exception": e})
        return errors

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

    def get_pods(self, field_selector="", label_selector=""):
        api_response = self.v1.list_namespaced_pod(
            namespace=self.namespace,
            pretty=self.pretty,
            field_selector=field_selector,
            label_selector=label_selector,
        )
        return api_response.items

    def get_services_by_label(self, label_selector):
        api_response = self.v1.list_namespaced_service(
            namespace=self.namespace,
            pretty=self.pretty,
            label_selector=label_selector,
        )
        return api_response.items

    def delete_job(self, job_id):
        label_selector = "run={}".format(job_id)

        # query pods then delete
        pods = self.get_pods(label_selector=label_selector)
        pod_names = [pod.metadata.name for pod in pods]
        pod_errors = self.cleanup_pods(pod_names)

        # query services then delete
        services = self.get_services_by_label(label_selector)
        service_errors = self.cleanup_services(services)

        errors = pod_errors + service_errors
        return errors

    def pod_exec(self, pod_name, exec_command, timeout=60):
        """work as the command (with timeout): kubectl exec 'pod_name' 'exec_command'"""
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
            logging.warning("Exec on pod {} failed. cmd: {}, err: {}.".format(pod_name, exec_command, err))
            status_code = int(err["details"]["causes"][0]["message"])
        output = client.read_channel(STDOUT_CHANNEL) + client.read_channel(STDERR_CHANNEL)
        logging.info("Exec on pod {}, status: {}, cmd: {}, output: {}".format(pod_name, status_code, exec_command, output))
        return [status_code, output]
