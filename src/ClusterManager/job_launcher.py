#!/usr/bin/env python

import json
import yaml
import os
import logging
import logging.config
import timeit
import functools
import time
import datetime
import base64
import multiprocessing
import hashlib

from kubernetes import client, config as k8s_config
from kubernetes.client.rest import ApiException
from kubernetes.stream import stream
from kubernetes.stream.ws_client import ERROR_CHANNEL, STDERR_CHANNEL, STDOUT_CHANNEL

from prometheus_client import Histogram

import k8sUtils
from DataHandler import DataHandler
from job import Job, JobSchema
from pod_template import PodTemplate
from dist_pod_template import DistPodTemplate
from config import config

from cluster_manager import record

logger = logging.getLogger(__name__)

# The config will be loaded from default location.
k8s_config.load_kube_config()
k8s_CoreAPI = client.CoreV1Api()
k8s_AppsAPI = client.AppsV1Api()

class JobDeployer:
    def __init__(self):
        self.k8s_CoreAPI = k8s_CoreAPI
        self.k8s_AppsAPI = k8s_AppsAPI
        self.namespace = "default"
        self.pretty = "pretty_example"

    @record
    def _create_pod(self, body):
        api_response = self.k8s_CoreAPI.create_namespaced_pod(
            namespace=self.namespace,
            body=body,
            pretty=self.pretty,
        )
        return api_response

    @record
    def _delete_pod(self, name, grace_period_seconds=None):
        body = client.V1DeleteOptions()
        body.grace_period_seconds = grace_period_seconds
        api_response = self.k8s_CoreAPI.delete_namespaced_pod(
            name=name,
            namespace=self.namespace,
            pretty=self.pretty,
            body=body,
            grace_period_seconds=grace_period_seconds,
        )
        return api_response

    @record
    def _create_deployment(self, body):
        api_response = self.k8s_AppsAPI.create_namespaced_deployment(
            namespace=self.namespace,
            body=body,
            pretty=self.pretty,
        )
        return api_response

    @record
    def _delete_deployment(self, name, grace_period_seconds=None):
        body = client.V1DeleteOptions()
        body.grace_period_seconds = grace_period_seconds
        api_response = self.k8s_AppsAPI.delete_namespaced_deployment(
            name=name,
            namespace=self.namespace,
            pretty=self.pretty,
            body=body,
            grace_period_seconds=grace_period_seconds,
        )
        return api_response

    @record
    def _create_service(self, body):
        api_response = self.k8s_CoreAPI.create_namespaced_service(
            namespace=self.namespace,
            body=body,
            pretty=self.pretty,
        )
        return api_response

    @record
    def _delete_service(self, name):
        api_response = self.k8s_CoreAPI.delete_namespaced_service(
            name=name,
            namespace=self.namespace,
            pretty=self.pretty,
            body=client.V1DeleteOptions(),
        )
        return api_response

    @record
    def _create_secret(self, body):
        api_response = self.k8s_CoreAPI.create_namespaced_secret(
            namespace=self.namespace,
            body=body,
            pretty=self.pretty,
        )
        return api_response

    @record
    def _delete_secret(self, name, grace_period_seconds=None):
        body = client.V1DeleteOptions()
        body.grace_period_seconds = grace_period_seconds
        api_response = self.k8s_CoreAPI.delete_namespaced_secret(
            name=name,
            namespace=self.namespace,
            pretty=self.pretty,
            body=body,
            grace_period_seconds=grace_period_seconds
        )
        return api_response

    @record
    def _cleanup_pods(self, pod_names, force=False):
        errors = []
        grace_period_seconds = 0 if force else None
        for pod_name in pod_names:
            try:
                self._delete_pod(pod_name, grace_period_seconds)
            except Exception as e:
                if isinstance(e, ApiException) and 404 == e.status:
                    return []
                message = "Delete pod failed: {}".format(pod_name)
                logging.warning(message, exc_info=True)
                errors.append({"message": message, "exception": e})
        return errors

    @record
    def _cleanup_services(self, services):
        errors = []
        for service in services:
            assert(isinstance(service, client.V1Service))
            try:
                service_name = service.metadata.name
                self._delete_service(service_name)
            except ApiException as e:
                message = "Delete service failed: {}".format(service_name)
                logging.warning(message, exc_info=True)
                errors.append({"message": message, "exception": e})
        return errors

    @record
    def _cleanup_deployment(self, deployment_names, force=False):
        errors = []
        grace_period_seconds = 0 if force else None
        for deployment_name in deployment_names:
            try:
                self._delete_deployment(deployment_name, grace_period_seconds)
            except Exception as e:
                if isinstance(e, ApiException) and 404 == e.status:
                    return []
                message = "Delete pod failed: {}".format(deployment_name)
                logging.warning(message, exc_info=True)
                errors.append({"message": message, "exception": e})
        return errors

    @record
    def _cleanup_secrets(self, secret_names, force=False):
        errors = []
        grace_period_seconds = 0 if force else None
        for secret_name in secret_names:
            try:
                self._delete_secret(secret_name, grace_period_seconds)
            except Exception as e:
                if isinstance(e, ApiException) and 404 == e.status:
                    return []
                message = "Deleting secret failed: {}".format(secret_name)
                logging.warning(message, exc_info=True)
                errors.append({"message": message, "exception": e})
        return errors

    @record
    def create_pods(self, pods):
        # TODO instead of delete, we could check update existiong ones. During refactoring, keeping the old way.
        pod_names = [pod["metadata"]["name"] for pod in pods if pod["kind"] == "Pod"]
        self._cleanup_pods(pod_names)
        deployment_names = [pod["metadata"]["name"] for pod in pods if pod["kind"] == "Deployment"]
        self._cleanup_deployment(pod_names)
        created = []
        for pod in pods:
            if pod["kind"] == "Pod":
                created_pod = self._create_pod(pod)
            elif pod["kind"] == "Deployment":
                created_pod = self._create_deployment(pod)
            created.append(created_pod)
            logging.info("Create pod succeed: %s" % created_pod.metadata.name)
        return created

    @record
    def create_secrets(self, secrets):
        # Clean up secrets first
        secret_names = [secret["metadata"]["name"] for secret in secrets if secret["kind"] == "Secret"]
        logging.info("Trying to delete secrets %s" % secret_names)
        self._cleanup_secrets(secret_names)

        created = []
        for secret in secrets:
            created_secret = self._create_secret(secret)
            created.append(created_secret)
            logging.info("Creating secret succeeded: %s" % created_secret.metadata.name)
        return created

    @record
    def get_pods(self, field_selector="", label_selector=""):
        api_response = self.k8s_CoreAPI.list_namespaced_pod(
            namespace=self.namespace,
            pretty=self.pretty,
            field_selector=field_selector,
            label_selector=label_selector,
        )
        logging.debug("Get pods: {}".format(api_response))
        return api_response.items

    @record
    def _get_deployments(self, field_selector="", label_selector=""):
        api_response = self.k8s_AppsAPI.list_namespaced_deployment(
            namespace=self.namespace,
            pretty=self.pretty,
            field_selector=field_selector,
            label_selector=label_selector,
        )
        logging.debug("Get pods: {}".format(api_response))
        return api_response.items

    @record
    def _get_services_by_label(self, label_selector):
        api_response = self.k8s_CoreAPI.list_namespaced_service(
            namespace=self.namespace,
            pretty=self.pretty,
            label_selector=label_selector,
        )
        return api_response.items

    @record
    def get_secrets(self, field_selector="", label_selector=""):
        api_response = self.k8s_CoreAPI.list_namespaced_secret(
            namespace=self.namespace,
            pretty=self.pretty,
            field_selector=field_selector,
            label_selector=label_selector,
        )
        logging.debug("Get secrets: {}".format(api_response))
        return api_response.items

    @record
    def delete_job(self, job_id, force=False):
        label_selector = "run={}".format(job_id)

        # query pods then delete
        pods = self.get_pods(label_selector=label_selector)
        pod_names = [pod.metadata.name for pod in pods]
        pod_errors = self._cleanup_pods(pod_names, force)
        logging.info("deleting pods %s" % ",".join(pod_names))
        # query services then delete
        services = self._get_services_by_label(label_selector)
        service_errors = self._cleanup_services(services)

        deployments = self._get_deployments(label_selector=label_selector)
        deployment_names = [deployment.metadata.name for deployment in deployments]
        deployment_errors = self._cleanup_deployment(deployment_names, force)

        logging.info("deleting deployments %s" % ",".join(deployment_names))

        # query and delete secrets
        secrets = self.get_secrets(label_selector=label_selector)
        secret_names = [secret.metadata.name for secret in secrets]
        secret_errors = self._cleanup_secrets(secret_names, force)
        logging.info("deleting secrets %s" % ",".join(secret_names))

        errors = pod_errors + service_errors + deployment_errors + secret_errors
        return errors

    @record
    def pod_exec(self, pod_name, exec_command, timeout=60):
        """work as the command (with timeout): kubectl exec 'pod_name' 'exec_command'"""
        try:
            logging.info("Exec on pod {}: {}".format(pod_name, exec_command))
            client = stream(
                self.k8s_CoreAPI.connect_get_namespaced_pod_exec,
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


class JobRole(object):
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
            job_role = JobRole(role, pod_name, pod)
            job_roles.append(job_role)
        return job_roles

    def __init__(self, role_name, pod_name, pod):
        self.role_name = role_name
        self.pod_name = pod_name
        self.pod = pod

    # will query api server if refresh is True
    def status(self, refresh=False):
        """
        Return role status in ["NotFound", "Pending", "Running", "Succeeded", "Failed", "Unknown"]
        It's slightly different from pod phase, when pod is running:
            CONTAINER_READY -> WORKER_READY -> JOB_READY (then the job finally in "Running" status.)
        """
        # pod-phase: https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#pod-phase
        # node condition: https://kubernetes.io/docs/concepts/architecture/nodes/#condition
        if refresh:
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
            if not self._is_role_ready():
                return "Pending"

        return phase

    def pod_details(self):
        return self.pod

    def _is_file_exist(self, file):
        deployer = JobDeployer()
        status_code, _ = deployer.pod_exec(self.pod_name, ["/bin/sh", "-c", "ls -lrt {}".format(file)])
        return status_code == 0

    def _is_role_ready(self):
        for container in self.pod.spec.containers:
            if container.name == self.pod_name and container.readiness_probe is not None:
                for status in self.pod.status.container_statuses:
                    if status.name == self.pod_name:
                        logger.info("pod %s have readiness_probe result", self.pod_name)
                        return status.ready
        # no readiness_probe defined, fallback to old way
        return self._is_file_exist(JobRole.MARK_ROLE_READY_FILE)


# Interface class for managing life time of job
class Launcher(object):
    def __init__(self):
        pass

    def start(self):
        pass

    def submit_job(self, job_desc):
        pass

    def kill_job(self, job_id, desired_state="killed"):
        pass

def get_job_status_detail(job):
    if "jobStatusDetail" not in job:
        return None

    job_status_detail = job["jobStatusDetail"]
    if job_status_detail is None:
        return job_status_detail

    if not isinstance(job_status_detail, list):
        job_status_detail = base64.b64decode(job_status_detail)
        job_status_detail = json.loads(job_status_detail)
    return job_status_detail


def job_status_detail_with_finished_time(job_status_detail, status, msg=""):
    # This method is called when a job succeeds/fails/is killed/has an error

    # job_status_detail must be None or a list
    if (job_status_detail is not None) and (not isinstance(job_status_detail, list)):
        return job_status_detail

    # Force adding an item for empty detail
    if (job_status_detail is None) or (len(job_status_detail) == 0):
        job_status_detail = [{}]

    finished_at = k8sUtils.localize_time(datetime.datetime.now())
    new_job_status_detail = []
    # Override finishedAt for all pods if absent
    for pod_status_detail in job_status_detail:
        # Mark started time the same as finished time for a fast finishing job
        if "startedAt" not in pod_status_detail:
            pod_status_detail["startedAt"] = finished_at

        if "finishedAt" not in pod_status_detail:
            pod_status_detail["finishedAt"] = finished_at

        pod_status_detail["message"] = "{} at {}. {}".format(status, finished_at, msg)
        new_job_status_detail.append(pod_status_detail)

    return new_job_status_detail


class PythonLauncher(Launcher):
    def __init__(self, pool_size=3):
        self.processes = []
        self.queue = None
        self.pool_size = pool_size
        # items in queue should be tuple of 3 elements: (function name, args, kwargs)

    def start(self):
        if len(self.processes) == 0:
            self.queue = multiprocessing.JoinableQueue()

            for i in range(self.pool_size):
                p = multiprocessing.Process(target=self.run,
                        args=(self.queue,), name="py-launcher-" + str(i))
                self.processes.append(p)
                p.start()

    def wait_tasks_done(self):
        self.queue.join()

    def _all_pods_not_existing(self, job_id):
        job_deployer = JobDeployer()
        job_roles = JobRole.get_job_roles(job_id)
        statuses = [job_role.status() for job_role in job_roles]
        logging.info("Job: {}, status: {}".format(job_id, statuses))
        return all([status == "NotFound" for status in statuses])

    def submit_job(self, job):
        self.queue.put(("submit_job", (job,), {}))

    def submit_job_impl(self, job):
        # check if existing any pod with label: run=job_id
        assert("jobId" in job)
        job_id = job["jobId"]
        if not self._all_pods_not_existing(job_id):
            logging.warning("Waiting until previously pods are cleaned up! Job {}".format(job_id))
            job_deployer = JobDeployer()
            errors = job_deployer.delete_job(job_id, force=True)
            if errors:
                logging.warning("Force delete job {}: {}".format(job_id, errors))
            return

        ret = {}
        dataHandler = DataHandler()

        try:
            # TODO refine later
            # before resubmit the job, reset the endpoints
            # update all endpoint to status 'pending', so it would restart when job is ready
            endpoints = dataHandler.GetJobEndpoints(job_id)
            for endpoint_id, endpoint in endpoints.items():
                endpoint["status"] = "pending"
                logging.info("Reset endpoint status to 'pending': {}".format(endpoint_id))
                dataHandler.UpdateEndpoint(endpoint)

            job["cluster"] = config
            job_object, errors = JobSchema().load(job)
            # TODO assert job_object is a Job
            assert isinstance(job_object, Job), "job_object is not of Job, but " + str(type(job_object))

            job_object.params = json.loads(base64.b64decode(job["jobParams"]))

            # inject gid, uid and user
            # TODO it should return only one entry
            user_info = dataHandler.GetIdentityInfo(job_object.params["userName"])[0]
            job_object.params["gid"] = user_info["gid"]
            job_object.params["uid"] = user_info["uid"]
            job_object.params["user"] = job_object.get_alias()

            if "job_token" not in job_object.params:
                if "user_sign_token" in config and "userName" in job_object.params:
                    job_object.params["job_token"] = hashlib.md5(job_object.params["userName"]+":"+config["user_sign_token"]).hexdigest()
                else:
                    job_object.params["job_token"] = "tryme2017"

            if "envs" not in job_object.params:
                job_object.params["envs"] =[]
            job_object.params["envs"].append({"name": "DLTS_JOB_TOKEN", "value": job_object.params["job_token"]})              


            enable_custom_scheduler = job_object.is_custom_scheduler_enabled()
            secret_template = job_object.get_blobfuse_secret_template()
            if job_object.params["jobtrainingtype"] == "RegularJob":
                pod_template = PodTemplate(job_object.get_template(),
                                           enable_custom_scheduler=enable_custom_scheduler,
                                           secret_template=secret_template)
            elif job_object.params["jobtrainingtype"] == "PSDistJob":
                pod_template = DistPodTemplate(job_object.get_template(),
                                               secret_template=secret_template)
            elif job_object.params["jobtrainingtype"] == "InferenceJob":
                pod_template = PodTemplate(job_object.get_template(),
                                           deployment_template=job_object.get_deployment_template(),
                                           enable_custom_scheduler=False,
                                           secret_template=secret_template)
            else:
                dataHandler.SetJobError(job_object.job_id, "ERROR: invalid jobtrainingtype: %s" % job_object.params["jobtrainingtype"])
                dataHandler.Close()
                return False

            pods, error = pod_template.generate_pods(job_object)
            if error:
                dataHandler.SetJobError(job_object.job_id, "ERROR: %s" % error)
                dataHandler.Close()
                return False

            job_description = "\n---\n".join([yaml.dump(pod) for pod in pods])
            job_description_path = "jobfiles/" + time.strftime("%y%m%d") + "/" + job_object.job_id + "/" + job_object.job_id + ".yaml"
            local_jobDescriptionPath = os.path.realpath(os.path.join(config["storage-mount-path"], job_description_path))
            if not os.path.exists(os.path.dirname(local_jobDescriptionPath)):
                os.makedirs(os.path.dirname(local_jobDescriptionPath))
            with open(local_jobDescriptionPath, 'w') as f:
                f.write(job_description)

            secrets = pod_template.generate_secrets(job_object)

            job_deployer = JobDeployer()
            try:
                secrets = job_deployer.create_secrets(secrets)
                ret["output"] = "Created secrets: {}. ".format([secret.metadata.name for secret in secrets])
                pods = job_deployer.create_pods(pods)
                ret["output"] += "Created pods: {}".format([pod.metadata.name for pod in pods])
            except Exception as e:
                ret["output"] = "Error: %s" % e.message
                logging.error(e, exc_info=True)

            ret["jobId"] = job_object.job_id

            dataHandler.UpdateJobTextField(job_object.job_id, "jobStatus", "scheduling")
            dataHandler.UpdateJobTextField(job_object.job_id, "jobDescriptionPath", job_description_path)
            dataHandler.UpdateJobTextField(job_object.job_id, "jobDescription", base64.b64encode(job_description))
            dataHandler.UpdateJobTextField(job_object.job_id, "lastUpdated", datetime.datetime.now().isoformat())

            jobMeta = {}
            jobMeta["jobDescriptionPath"] = job_description_path
            jobMeta["jobPath"] = job_object.job_path
            jobMeta["workPath"] = job_object.work_path
            # the command of the first container
            jobMeta["LaunchCMD"] = pods[0].spec.containers[0].command

            jobMetaStr = base64.b64encode(json.dumps(jobMeta))
            dataHandler.UpdateJobTextField(job_object.job_id, "jobMeta", jobMetaStr)
        except Exception as e:
            logging.error("Submit job failed: %s" % job, exc_info=True)
            ret["error"] = str(e)
            retries = dataHandler.AddandGetJobRetries(job["jobId"])
            if retries >= 5:
                dataHandler.UpdateJobTextField(job["jobId"], "jobStatus", "error")
                dataHandler.UpdateJobTextField(job["jobId"], "errorMsg", "Cannot submit job!" + str(e))

                detail = get_job_status_detail(job)
                detail = job_status_detail_with_finished_time(detail, "error", "Server error in job submission")
                dataHandler.UpdateJobTextField(job["jobId"], "jobStatusDetail", base64.b64encode(json.dumps(detail)))

                # Try to clean up the job
                try:
                    job_deployer = JobDeployer()
                    job_deployer.delete_job(job_id, force=True)
                    logging.info("Cleaning up job %s succeeded after %d retries of job submission" % (job["jobId"], retries))
                except:
                    logging.warning("Cleaning up job %s failed after %d retries of job submission" % (job["jobId"], retries))

        dataHandler.Close()
        return ret

    def kill_job(self, job_id, desired_state="killed"):
        self.queue.put(("kill_job", (job_id,), {"desired_state": desired_state}))

    def kill_job_impl(self, job_id, desired_state="killed", dataHandlerOri=None):
        if dataHandlerOri is None:
            dataHandler = DataHandler()
        else:
            dataHandler = dataHandlerOri

        # TODO: Use JobDeployer?
        result, detail = k8sUtils.GetJobStatus(job_id)
        detail = job_status_detail_with_finished_time(detail, desired_state)
        dataHandler.UpdateJobTextField(job_id, "jobStatusDetail", base64.b64encode(json.dumps(detail)))
        logging.info("Killing job %s, with status %s, %s" % (job_id, result, detail))

        job_deployer = JobDeployer()
        errors = job_deployer.delete_job(job_id, force=True)

        if len(errors) == 0:
            dataHandler.UpdateJobTextField(job_id, "jobStatus", desired_state)
            dataHandler.UpdateJobTextField(job_id, "lastUpdated", datetime.datetime.now().isoformat())
            if dataHandlerOri is None:
                dataHandler.Close()
            return True
        else:
            dataHandler.UpdateJobTextField(job_id, "jobStatus", "error", "{}".format(errors))
            dataHandler.UpdateJobTextField(job_id, "lastUpdated", datetime.datetime.now().isoformat())
            if dataHandlerOri is None:
                dataHandler.Close()
            logging.error("Kill job failed with errors: {}".format(errors))
            return False

    def run(self, queue):
        # TODO maintain a data_handler so do not need to init it every time
        while True:
            func_name, args, kwargs = queue.get(True)

            try:
                if func_name == "submit_job":
                    self.submit_job_impl(*args, **kwargs)
                elif func_name == "kill_job":
                    self.kill_job_impl(*args, **kwargs)
                else:
                    logger.error("unknown func_name %s, with args %s %s",
                            func_name, args, kwargs)
            except Exception:
                logging.exception("processing job failed")
            finally:
                queue.task_done()
