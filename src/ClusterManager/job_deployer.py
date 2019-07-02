import yaml
import os
import logging
from kubernetes import client, config


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
            #  grace_period_seconds=grace_period_seconds,
            #  orphan_dependents=orphan_dependents,
            #  propagation_policy=propagation_policy,
        )
        pass

    def cleanup_pods(self, pods):
        for pod in pods:
            try:
                pod_name = pod["metadata"]["name"]
                self.delete_pod(pod_name)
            except Exception as e:
                logging.warning("Delete pod failed: %s!" % pod_name, exc_info=True)

    def create_pods(self, pods):
        # TODO instead of delete, we could check update existiong ones. During refactoring, keeping the old way.
        self.cleanup_pods(pods)
        created = []
        for pod in pods:
            self.create_pod(pod)
            pod_name = pod["metadata"]["name"]
            created.append(pod_name)
            logging.info("Create pod succeed: %s" % pod_name)
        return created
