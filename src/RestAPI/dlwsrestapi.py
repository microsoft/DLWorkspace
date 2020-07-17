#!/usr/bin/env python3
import sys
import json
import os
import base64
import yaml
import logging
from logging.config import dictConfig

from flask import Flask, Response
from flask_restful import reqparse, Api, Resource
from flask import request, jsonify
from flask_cors import CORS
import prometheus_client

sys.path.append(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "../utils"))

import JobRestAPIUtils
from authorization import ResourceType, Permission, AuthorizationManager, ACLManager
from config import config, global_vars
import authorization
from DataHandler import DataHandler

CONTENT_TYPE_LATEST = str("text/plain; version=0.0.4; charset=utf-8")


def base64encode(str_val):
    return base64.b64encode(str_val.encode("utf-8")).decode("utf-8")


def base64decode(str_val):
    return base64.b64decode(str_val.encode("utf-8")).decode("utf-8")


dir_path = os.path.dirname(os.path.realpath(__file__))
with open(os.path.join(dir_path, "logging.yaml"), "r") as f:
    logging_config = yaml.load(f)
    dictConfig(logging_config)
logger = logging.getLogger("restfulapi")

app = Flask(__name__)
CORS(app)
api = Api(app)
verbose = True
logger.info("Restful API started with config %s", config)

if "initAdminAccess" not in global_vars or not global_vars["initAdminAccess"]:
    logger.info("===========Init Admin Access===============")
    global_vars["initAdminAccess"] = True
    logger.info("setting admin access!")
    ACLManager.UpdateAce(
        "Administrator",
        AuthorizationManager.GetResourceAclPath("", ResourceType.Cluster),
        Permission.Admin, 0)
    logger.info("admin access given!")


def istrue(value):
    if isinstance(value, bool):
        return value
    elif isinstance(value, str):
        return value.lower()[0] == "y"
    else:
        return bool(value)


def tolist(value):
    if isinstance(value, str):
        if len(value) > 0:
            return [value]
        else:
            return []
    else:
        return value


def remove_creds(job):
    job_params = job.get("jobParams", None)
    if job_params is None:
        return

    plugins = job_params.get("plugins", None)
    if plugins is None or not isinstance(plugins, dict):
        return

    blobfuse = plugins.get("blobfuse", None)
    if blobfuse is not None and isinstance(blobfuse, list):
        for bf in blobfuse:
            bf.pop("accountName", None)
            bf.pop("accountKey", None)

    image_pull = plugins.get("imagePull", None)
    if image_pull is not None and isinstance(image_pull, list):
        for i_p in image_pull:
            i_p.pop("username", None)
            i_p.pop("password", None)


@api.resource("/PostJob")
class PostJob(Resource):
    def post(self):
        params = request.get_json(force=True)

        ret = {}
        output = JobRestAPIUtils.SubmitJob(json.dumps(params))

        if "jobId" in output:
            ret["jobId"] = output["jobId"]
        else:
            if "error" in output:
                ret["error"] = "Cannot create job!" + output["error"]
            else:
                ret["error"] = "Cannot create job!"

        logger.info("Submit job output is %s, ret is %s", output, ret)
        return jsonify(ret)


@api.resource("/ListJobs")
class ListJobs(Resource):
    def __init__(self):
        self.get_parser = reqparse.RequestParser()
        self.get_parser.add_argument("userName", required=True)
        self.get_parser.add_argument("vcName", required=True)
        self.get_parser.add_argument("jobOwner", required=True)
        self.get_parser.add_argument("num", type=int, default=20)

    def get(self):
        args = self.get_parser.parse_args()
        username = args["userName"]
        vc_name = args["vcName"]
        job_owner = args["jobOwner"]
        num = args["num"]
        jobs = JobRestAPIUtils.get_job_list(username, vc_name, job_owner, num)

        queuedJobs = []
        runningJobs = []
        finishedJobs = []
        visualizationJobs = []
        for job in jobs:
            job.pop("jobDescription", None)

            job["jobParams"] = json.loads(base64decode(job["jobParams"]))

            if "endpoints" in job and job["endpoints"] is not None and len(
                    job["endpoints"].strip()) > 0:
                job["endpoints"] = json.loads(job["endpoints"])

            if "jobStatusDetail" in job and job[
                    "jobStatusDetail"] is not None and len(
                        job["jobStatusDetail"].strip()) > 0:
                try:
                    s = job["jobStatusDetail"]
                    s = base64decode(s)
                    s = json.loads(s)
                    job["jobStatusDetail"] = s
                except Exception as e:
                    job["jobStatusDetail"] = s

            # Remove credentials
            remove_creds(job)

            if job["jobStatus"] == "running":
                if job["jobType"] == "training":
                    runningJobs.append(job)
                elif job["jobType"] == "visualization":
                    visualizationJobs.append(job)
            elif job["jobStatus"] == "queued" or job[
                    "jobStatus"] == "scheduling" or job[
                        "jobStatus"] == "unapproved":
                queuedJobs.append(job)
            else:
                finishedJobs.append(job)

        ret = {}
        ret["queuedJobs"] = queuedJobs
        ret["runningJobs"] = runningJobs
        ret["finishedJobs"] = finishedJobs
        ret["visualizationJobs"] = visualizationJobs
        ret["meta"] = {
            "queuedJobs": len(queuedJobs),
            "runningJobs": len(runningJobs),
            "finishedJobs": len(finishedJobs),
            "visualizationJobs": len(visualizationJobs)
        }
        return jsonify(ret)


@api.resource("/ListJobsV2")
class ListJobsV2(Resource):
    def __init__(self):
        self.get_parser = reqparse.RequestParser()
        self.get_parser.add_argument("userName", required=True)
        self.get_parser.add_argument("vcName", required=True)
        self.get_parser.add_argument("jobOwner", required=True)
        self.get_parser.add_argument("num", type=int, default=20)

    def get(self):
        args = self.get_parser.parse_args()
        username = args["userName"]
        vc_name = args["vcName"]
        job_owner = args["jobOwner"]
        num = args["num"]

        jobs = JobRestAPIUtils.get_job_list_v2(username, vc_name, job_owner,
                                               num)

        for _, job_list in jobs.items():
            if isinstance(job_list, list):
                for job in job_list:
                    remove_creds(job)

        return jsonify(jobs)


@api.resource("/ListActiveJobs")
class ListActiveJobs(Resource):
    def get(self):
        return JobRestAPIUtils.get_active_job_list()


@api.resource("/KillJob")
class KillJob(Resource):
    def __init__(self):
        self.get_parser = reqparse.RequestParser()
        self.get_parser.add_argument("jobId", required=True)
        self.get_parser.add_argument("userName", required=True)
        self.get_parser.add_argument("desc", required=False)

    def get(self):
        args = self.get_parser.parse_args()
        job_id = args["jobId"]
        username = args["userName"]
        desc = args.get("desc")
        result = JobRestAPIUtils.kill_job(username, job_id, desc)
        ret = {}
        if result:
            # NOTE "Success" prefix is used in reaper, please also update reaper code
            # if need to change it.
            ret["result"] = "Success, the job is scheduled to be terminated."
        else:
            ret["result"] = "Cannot Kill the job. Job ID:" + job_id

        return jsonify(ret)


@api.resource("/PauseJob")
class PauseJob(Resource):
    def __init__(self):
        self.get_parser = reqparse.RequestParser()
        self.get_parser.add_argument("jobId", required=True)
        self.get_parser.add_argument("userName", required=True)

    def get(self):
        args = self.get_parser.parse_args()
        job_id = args["jobId"]
        username = args["userName"]
        result = JobRestAPIUtils.pause_job(username, job_id)
        ret = {}
        if result:
            ret["result"] = "Success, the job is scheduled to be paused."
        else:
            ret["result"] = "Cannot pause the job. Job ID:" + job_id

        return jsonify(ret)


@api.resource("/ResumeJob")
class ResumeJob(Resource):
    def __init__(self):
        self.get_parser = reqparse.RequestParser()
        self.get_parser.add_argument("jobId", required=True)
        self.get_parser.add_argument("userName", required=True)

    def get(self):
        args = self.get_parser.parse_args()
        job_id = args["jobId"]
        username = args["userName"]
        result = JobRestAPIUtils.resume_job(username, job_id)
        ret = {}
        if result:
            ret["result"] = "Success, the job is scheduled to be resumed."
        else:
            ret["result"] = "Cannot resume the job. Job ID:" + job_id

        return jsonify(ret)


@api.resource("/ApproveJob")
class ApproveJob(Resource):
    def __init__(self):
        self.get_parser = reqparse.RequestParser()
        self.get_parser.add_argument("jobId", required=True)
        self.get_parser.add_argument("userName", required=True)

    def get(self):
        args = self.get_parser.parse_args()
        job_id = args["jobId"]
        username = args["userName"]
        result = JobRestAPIUtils.approve_job(username, job_id)
        ret = {}
        if result:
            ret["result"] = "Success, the job has been approved."
        else:
            ret["result"] = "Cannot approve the job. Job ID:" + job_id

        return jsonify(ret)


@api.resource("/ScaleJob")
class ScaleJob(Resource):
    def __init__(self):
        self.post_parser = reqparse.RequestParser()
        self.post_parser.add_argument("jobId", required=True)
        self.post_parser.add_argument("userName", required=True)
        self.post_parser.add_argument("mingpu", required=True)
        self.post_parser.add_argument("maxgpu", required=True)

    def post(self):
        args = self.post_parser.parse_args()
        job_id = args["jobId"]
        username = args["userName"]
        mingpu = int(args["mingpu"])
        maxgpu = int(args["maxgpu"])
        msg, status_code = JobRestAPIUtils.scale_inference_job(
            username, job_id, mingpu, maxgpu)
        if status_code != 200:
            return msg, status_code

        return jsonify(msg)


@api.resource("/KillJobs")
class KillJobs(Resource):
    def __init__(self):
        self.get_parser = reqparse.RequestParser()
        self.get_parser.add_argument("jobIds", required=True)
        self.get_parser.add_argument("userName", required=True)

    def get(self):
        args = self.get_parser.parse_args()
        job_ids = args["jobIds"]
        username = args["userName"]
        result = JobRestAPIUtils.kill_jobs(username, job_ids)
        ret = {"result": result}

        return jsonify(ret)


@api.resource("/PauseJobs")
class PauseJobs(Resource):
    def __init__(self):
        self.get_parser = reqparse.RequestParser()
        self.get_parser.add_argument("jobIds", required=True)
        self.get_parser.add_argument("userName", required=True)

    def get(self):
        args = self.get_parser.parse_args()
        job_ids = args["jobIds"]
        username = args["userName"]
        result = JobRestAPIUtils.pause_jobs(username, job_ids)
        ret = {"result": result}

        return jsonify(ret)


@api.resource("/ResumeJobs")
class ResumeJobs(Resource):
    def __init__(self):
        self.get_parser = reqparse.RequestParser()
        self.get_parser.add_argument("jobIds", required=True)
        self.get_parser.add_argument("userName", required=True)

    def get(self):
        args = self.get_parser.parse_args()
        job_ids = args["jobIds"]
        username = args["userName"]
        result = JobRestAPIUtils.resume_jobs(username, job_ids)
        ret = {"result": result}

        return jsonify(ret)


@api.resource("/ApproveJobs")
class ApproveJobs(Resource):
    def __init__(self):
        self.get_parser = reqparse.RequestParser()
        self.get_parser.add_argument("jobIds", required=True)
        self.get_parser.add_argument("userName", required=True)

    def get(self):
        args = self.get_parser.parse_args()
        job_ids = args["jobIds"]
        username = args["userName"]
        result = JobRestAPIUtils.approve_jobs(username, job_ids)
        ret = {"result": result}

        return jsonify(ret)


@api.resource("/GetJobDetail")
class GetJobDetail(Resource):
    def __init__(self):
        self.get_parser = reqparse.RequestParser()
        self.get_parser.add_argument("jobId", required=True)
        self.get_parser.add_argument("userName", required=True)

    def get(self):
        args = self.get_parser.parse_args()
        jobId = args["jobId"]
        userName = args["userName"]
        job = JobRestAPIUtils.GetJobDetail(userName, jobId)
        job["jobParams"] = json.loads(base64decode(job["jobParams"]))
        if "endpoints" in job and job["endpoints"] is not None and len(
                job["endpoints"].strip()) > 0:
            job["endpoints"] = json.loads(job["endpoints"])
        if "jobStatusDetail" in job and job[
                "jobStatusDetail"] is not None and len(
                    job["jobStatusDetail"].strip()) > 0:
            try:
                job["jobStatusDetail"] = json.loads(
                    base64decode(job["jobStatusDetail"]))
            except Exception as e:
                pass
        if "jobMeta" in job:
            job.pop("jobMeta", None)

        # Remove credentials
        remove_creds(job)

        return jsonify(job)


@api.resource("/GetJobDetailV2")
class GetJobDetailV2(Resource):
    def __init__(self):
        self.get_parser = reqparse.RequestParser()
        self.get_parser.add_argument("jobId", required=True)
        self.get_parser.add_argument("userName", required=True)

    def get(self):
        args = self.get_parser.parse_args()
        jobId = args["jobId"]
        userName = args["userName"]
        job = JobRestAPIUtils.GetJobDetailV2(userName, jobId)
        remove_creds(job)
        return jsonify(job)


@api.resource("/GetJobLog")
class GetJobLog(Resource):
    def __init__(self):
        self.get_parser = reqparse.RequestParser()
        self.get_parser.add_argument("jobId", required=True)
        self.get_parser.add_argument("userName", required=True)
        self.get_parser.add_argument("cursor")

    def get(self):
        args = self.get_parser.parse_args()
        jobId = args["jobId"]
        userName = args["userName"]
        cursor = args["cursor"]
        return JobRestAPIUtils.GetJobLog(userName, jobId, cursor)


@app.route("/GetJobRawLog")
def GetJobRawLog():
    get_parser = reqparse.RequestParser()
    get_parser.add_argument("jobId", required=True)
    get_parser.add_argument("userName", required=True)
    args = get_parser.parse_args()
    jobId = args["jobId"]
    userName = args["userName"]
    response = JobRestAPIUtils.GetJobRawLog(userName, jobId)
    if type(response) is int:
        return Response(status=response, content_type="text/plain")
    else:
        return Response(response, content_type="text/plain")


@api.resource("/GetJobStatus")
class GetJobStatus(Resource):
    def __init__(self):
        self.get_parser = reqparse.RequestParser()
        self.get_parser.add_argument("jobId", required=True)

    def get(self):
        args = self.get_parser.parse_args()
        jobId = args["jobId"]
        return jsonify(JobRestAPIUtils.GetJobStatus(jobId))


@api.resource("/GetClusterStatus")
class GetClusterStatus(Resource):
    def __init__(self):
        self.get_parser = reqparse.RequestParser()
        self.get_parser.add_argument("userName", required=True)

    def get(self):
        args = self.get_parser.parse_args()
        userName = args["userName"]
        cluster_status, last_updated_time = JobRestAPIUtils.GetClusterStatus()
        cluster_status["last_updated_time"] = last_updated_time
        return jsonify(cluster_status)


@api.resource("/AddUser")
class AddUser(Resource):
    def __init__(self):
        self.get_parser = reqparse.RequestParser()
        self.get_parser.add_argument("userName", required=True)
        self.get_parser.add_argument("uid", required=True)
        self.get_parser.add_argument("gid", required=True)
        self.get_parser.add_argument("groups", default=[])
        self.get_parser.add_argument("public_key", required=True)
        self.get_parser.add_argument("private_key", required=True)

    def get(self):
        args = self.get_parser.parse_args()

        ret = {}
        userName = args["userName"]
        uid = args["uid"]
        gid = args["gid"]
        groups = args["groups"]
        public_key = args["public_key"]
        private_key = args["private_key"]

        ret["status"] = JobRestAPIUtils.AddUser(userName, uid, gid, groups,
                                                public_key, private_key)
        return jsonify(ret)


@api.resource("/GetAllUsers")
class GetAllUsers(Resource):
    def get(self):
        data_handler = None
        try:
            data_handler = DataHandler()
            ret = data_handler.GetUsers()
            ret = [(x[0], x[1]) for x in ret] # remove key info
            return jsonify(ret)
        except Exception as e:
            return "Internal Server Error. " + str(e), 400
        finally:
            if data_handler is not None:
                data_handler.Close()


@api.resource("/UpdateAce")
class UpdateAce(Resource):
    def __init__(self):
        self.get_parser = reqparse.RequestParser()
        self.get_parser.add_argument("userName", required=True)
        self.get_parser.add_argument("identityName", required=True)
        self.get_parser.add_argument("resourceType", required=True, type=int)
        self.get_parser.add_argument("resourceName", required=True)
        self.get_parser.add_argument("permissions", required=True, type=int)

    def get(self):
        args = self.get_parser.parse_args()
        username = args["userName"]
        identityName = args["identityName"]
        resourceType = args["resourceType"]
        resourceName = args["resourceName"]
        permissions = args["permissions"]
        ret = {}
        ret["result"] = JobRestAPIUtils.UpdateAce(username, identityName,
                                                  resourceType, resourceName,
                                                  permissions)
        return jsonify(ret)


@api.resource("/DeleteAce")
class DeleteAce(Resource):
    def __init__(self):
        self.get_parser = reqparse.RequestParser()
        self.get_parser.add_argument("userName", required=True)
        self.get_parser.add_argument("identityName", required=True)
        self.get_parser.add_argument("resourceType", required=True, type=int)
        self.get_parser.add_argument("resourceName", required=True)

    def get(self):
        args = self.get_parser.parse_args()
        username = args["userName"]
        identityName = args["identityName"]
        resourceType = args["resourceType"]
        resourceName = args["resourceName"]
        ret = {}
        ret["result"] = JobRestAPIUtils.DeleteAce(username, identityName,
                                                  resourceType, resourceName)
        return jsonify(ret)


@api.resource("/IsClusterAdmin")
class IsClusterAdmin(Resource):
    def __init__(self):
        self.get_parser = reqparse.RequestParser()
        self.get_parser.add_argument("userName", required=True)

    def get(self):
        args = self.get_parser.parse_args()
        username = args["userName"]
        ret = {}
        ret["result"] = AuthorizationManager.IsClusterAdmin(username)
        return jsonify(ret)


@api.resource("/GetACL")
class GetACL(Resource):
    def __init__(self):
        self.get_parser = reqparse.RequestParser()
        self.get_parser.add_argument("userName", required=True)

    def get(self):
        args = self.get_parser.parse_args()
        username = args["userName"]
        ret = {}
        ret["result"] = AuthorizationManager.GetAcl(username)
        return jsonify(ret)


@api.resource("/GetAllACL")
class GetAllACL(Resource):
    def get(self):
        ret = {}
        ret["result"] = ACLManager.GetAllAcl()
        return jsonify(ret)


@api.resource("/ListVCs")
class ListVCs(Resource):
    def __init__(self):
        self.get_parser = reqparse.RequestParser()
        self.get_parser.add_argument("userName", required=True)

    def get(self):
        args = self.get_parser.parse_args()
        userName = args["userName"]
        ret = {}
        ret["result"] = JobRestAPIUtils.ListVCs(userName)
        return jsonify(ret)


@api.resource("/GetVC")
class GetVC(Resource):
    def __init__(self):
        self.get_parser = reqparse.RequestParser()
        self.get_parser.add_argument("userName", required=True)
        self.get_parser.add_argument("vcName", required=True)

    def get(self):
        args = self.get_parser.parse_args()
        username = args["userName"]
        vc_name = args["vcName"]
        return jsonify(JobRestAPIUtils.get_vc(username, vc_name))


@api.resource("/GetVCV2")
class GetVCV2(Resource):
    def __init__(self):
        self.get_parser = reqparse.RequestParser()
        self.get_parser.add_argument("userName", required=True)
        self.get_parser.add_argument("vcName", required=True)

    def get(self):
        args = self.get_parser.parse_args()
        username = args["userName"]
        vc_name = args["vcName"]
        return jsonify(JobRestAPIUtils.get_vc_v2(username, vc_name))


@api.resource("/VCMeta")
class VCMeta(Resource):
    def __init__(self):
        self.get_parser = reqparse.RequestParser()
        self.get_parser.add_argument("userName", required=True)
        self.get_parser.add_argument("vcName", required=True)

        self.post_parser = reqparse.RequestParser()
        self.post_parser.add_argument("userName", required=True)
        self.post_parser.add_argument("vcName", required=True)

    def get(self):
        args = self.get_parser.parse_args()
        username = args["userName"]
        vc_name = args["vcName"]
        resp, code = JobRestAPIUtils.get_vc_meta(username, vc_name)
        return resp, code

    def post(self):
        args = self.post_parser.parse_args()
        username = args["userName"]
        vc_name = args["vcName"]

        vc_meta = request.get_json(silent=True)
        resp, code = JobRestAPIUtils.patch_vc_meta(username, vc_name, vc_meta)
        return resp, code


@api.resource("/ResourceQuota")
class ResourceQuota(Resource):
    def __init__(self):
        self.get_parser = reqparse.RequestParser()
        self.get_parser.add_argument("userName", required=True)

        self.post_parser = reqparse.RequestParser()
        self.post_parser.add_argument("userName", required=True)

    def get(self):
        args = self.get_parser.parse_args()
        username = args["userName"]
        resp, code = JobRestAPIUtils.get_resource_quota(username)
        return resp, code

    def post(self):
        args = self.post_parser.parse_args()
        username = args["userName"]
        resource_quota = request.get_json(silent=True)
        resp, code = JobRestAPIUtils.patch_resource_quota(username,
                                                             resource_quota)
        return resp, code


@api.resource("/PublicKey")
class PublicKey(Resource):
    def __init__(self):
        self.get_parser = reqparse.RequestParser()
        self.get_parser.add_argument("username", required=True)

        self.post_parser = reqparse.RequestParser()
        self.post_parser.add_argument("username", required=True)
        self.post_parser.add_argument("key_title", required=True)

        self.delete_parser = reqparse.RequestParser()
        self.delete_parser.add_argument("username", required=True)
        self.delete_parser.add_argument("key_id", required=True)

    def get(self):
        args = self.get_parser.parse_args()
        username = args["username"]
        return JobRestAPIUtils.list_public_keys(username)

    def post(self):
        args = self.post_parser.parse_args()
        username = args["username"]
        key_title = args["key_title"]

        val = request.get_json()
        public_key = val.get("public_key")
        if public_key is None or len(public_key) == 0:
            return {"error": "no public key provided"}, 400
        return JobRestAPIUtils.add_public_key(username, key_title, public_key)

    def delete(self):
        args = self.delete_parser.parse_args()
        username = args["username"]
        key_id = args["key_id"]
        return JobRestAPIUtils.delete_public_key(username, key_id)


@api.resource("/AddVC")
class AddVC(Resource):
    def __init__(self):
        self.get_parser = reqparse.RequestParser()
        self.get_parser.add_argument("userName", required=True)
        self.get_parser.add_argument("vcName", required=True)
        self.get_parser.add_argument("quota", required=True)
        self.get_parser.add_argument("metadata", required=True)

    def get(self):
        args = self.get_parser.parse_args()
        vcName = args["vcName"]
        quota = args["quota"]
        metadata = args["metadata"]
        userName = args["userName"]
        ret = {}
        ret["result"] = JobRestAPIUtils.AddVC(userName, vcName, quota, metadata)
        return jsonify(ret)


@api.resource("/DeleteVC")
class DeleteVC(Resource):
    def __init__(self):
        self.get_parser = reqparse.RequestParser()
        self.get_parser.add_argument("userName", required=True)
        self.get_parser.add_argument("vcName", required=True)

    def get(self):
        args = self.get_parser.parse_args()
        vcName = args["vcName"]
        userName = args["userName"]
        ret = {}
        ret["result"] = JobRestAPIUtils.DeleteVC(userName, vcName)
        return jsonify(ret)


@api.resource("/UpdateVC")
class UpdateVC(Resource):
    def __init__(self):
        self.get_parser = reqparse.RequestParser()
        self.get_parser.add_argument("userName", required=True)
        self.get_parser.add_argument("vcName", required=True)
        self.get_parser.add_argument("quota", required=True)
        self.get_parser.add_argument("metadata", required=True)

    def get(self):
        args = self.get_parser.parse_args()
        vcName = args["vcName"]
        quota = args["quota"]
        metadata = args["metadata"]
        userName = args["userName"]
        ret = {}
        ret["result"] = JobRestAPIUtils.UpdateVC(userName, vcName, quota,
                                                 metadata)

        return jsonify(ret)


@api.resource("/ListStorages")
class ListStorages(Resource):
    def __init__(self):
        self.get_parser = reqparse.RequestParser()
        self.get_parser.add_argument("userName", required=True)
        self.get_parser.add_argument("vcName", required=True)

    def get(self):
        args = self.get_parser.parse_args()
        vcName = args["vcName"]
        userName = args["userName"]
        ret = {}
        ret["result"] = JobRestAPIUtils.ListStorages(userName, vcName)
        return jsonify(ret)


@api.resource("/AddStorage")
class AddStorage(Resource):
    def __init__(self):
        self.get_parser = reqparse.RequestParser()
        self.get_parser.add_argument("userName", required=True)
        self.get_parser.add_argument("vcName", required=True)
        self.get_parser.add_argument("storageType", required=True)
        self.get_parser.add_argument("url", required=True)
        self.get_parser.add_argument("metadata", required=True)
        self.get_parser.add_argument("defaultMountPath", required=True)

    def get(self):
        args = self.get_parser.parse_args()
        vcName = args["vcName"]
        storageType = args["storageType"]
        url = args["url"]
        metadata = args["metadata"]
        defaultMountPath = args["defaultMountPath"]
        userName = args["userName"]
        ret = {}
        ret["result"] = JobRestAPIUtils.AddStorage(userName, vcName, url,
                                                   storageType, metadata,
                                                   defaultMountPath)
        return jsonify(ret)


@api.resource("/DeleteStorage")
class DeleteStorage(Resource):
    def __init__(self):
        self.get_parser = reqparse.RequestParser()
        self.get_parser.add_argument("userName", required=True)
        self.get_parser.add_argument("vcName", required=True)
        self.get_parser.add_argument("url", required=True)

    def get(self):
        args = self.get_parser.parse_args()
        vcName = args["vcName"]
        userName = args["userName"]
        url = args["url"]
        ret = {}
        ret["result"] = JobRestAPIUtils.DeleteStorage(userName, vcName, url)
        return jsonify(ret)


@api.resource("/UpdateStorage")
class UpdateStorage(Resource):
    def __init__(self):
        self.get_parser = reqparse.RequestParser()
        self.get_parser.add_argument("userName", required=True)
        self.get_parser.add_argument("vcName", required=True)
        self.get_parser.add_argument("storageType", required=True)
        self.get_parser.add_argument("url", required=True)
        self.get_parser.add_argument("metadata", required=True)
        self.get_parser.add_argument("defaultMountPath", required=True)

    def get(self):
        args = self.get_parser.parse_args()
        vcName = args["vcName"]
        storageType = args["storageType"]
        url = args["url"]
        metadata = args["metadata"]
        defaultMountPath = args["defaultMountPath"]
        userName = args["userName"]
        ret = {}
        ret["result"] = JobRestAPIUtils.UpdateStorage(userName, vcName, url,
                                                      storageType, metadata,
                                                      defaultMountPath)
        return jsonify(ret)


@api.resource("/endpoints")
class Endpoint(Resource):
    def __init__(self):
        self.get_parser = reqparse.RequestParser()
        self.get_parser.add_argument("jobId", required=True)
        self.get_parser.add_argument("userName", required=True)

        self.post_parser = reqparse.RequestParser()
        self.post_parser.add_argument("userName", required=True)

    def get(self):
        """return job["endpoints"]: curl -X GET /endpoints?jobId=...&userName=..."""
        args = self.get_parser.parse_args()
        jobId = args["jobId"]
        username = args["userName"]

        ret = JobRestAPIUtils.GetEndpoints(username, jobId)

        # TODO: return 403 error code
        # Return empty list for now to keep backward compatibility with old portal.
        return jsonify(ret)

    def post(self):
        """set job["endpoints"]: curl -X POST -H "Content-Type: application/json" /endpoints --data "{"jobId": ..., "endpoints": ["ssh", "ipython"] }"""
        args = self.post_parser.parse_args()
        username = args["userName"]

        params = request.get_json(silent=True)
        job_id = params["jobId"]
        requested_endpoints = params["endpoints"]

        interactive_ports = []
        # endpoints should be ["ssh", "ipython", "tensorboard", {"name": "port name", "podPort": "port on pod in 40000-49999"}]
        for interactive_port in [
                elem for elem in requested_endpoints
                if elem not in ["ssh", "ipython", "tensorboard", "theia"]
        ]:
            if any(required_field not in interactive_port
                   for required_field in ["name", "podPort"]):
                # if ["name", "port"] not in interactive_port:
                return (
                    "Bad request, interactive port should have \"name\" and \"podPort\"]: %s"
                    % requested_endpoints), 400
            if int(interactive_port["podPort"]) < 40000 or int(
                    interactive_port["podPort"]) > 49999:
                return (
                    "Bad request, interactive podPort should in range 40000-49999: %s"
                    % requested_endpoints), 400
            if len(interactive_port["name"]) > 16:
                return (
                    "Bad request, interactive port name length shoule be less than 16: %s"
                    % requested_endpoints), 400
            interactive_ports.append(interactive_port)

        msg, statusCode = JobRestAPIUtils.UpdateEndpoints(
            username, job_id, requested_endpoints, interactive_ports)
        if statusCode != 200:
            return msg, statusCode

        return jsonify(msg)


@api.resource("/templates")
class Templates(Resource):
    def __init__(self):
        self.get_parser = reqparse.RequestParser()
        self.get_parser.add_argument("vcName", required=True)
        self.get_parser.add_argument("userName", required=True)

        self.post_parser = reqparse.RequestParser()
        self.post_parser.add_argument("vcName", required=True, location="args")
        self.post_parser.add_argument("userName",
                                      required=True,
                                      location="args")
        self.post_parser.add_argument("database",
                                      required=True,
                                      location="args")
        self.post_parser.add_argument("templateName",
                                      required=True,
                                      location="args")

        self.delete_parser = self.post_parser.copy()

    def get(self):
        args = self.get_parser.parse_args()
        vcName = args["vcName"]
        userName = args["userName"]

        dataHandler = DataHandler()
        ret = dataHandler.GetTemplates("master") or []
        ret += dataHandler.GetTemplates("vc:" + vcName) or []
        ret += dataHandler.GetTemplates("user:" + userName) or []
        dataHandler.Close()
        return jsonify(ret)

    def post(self):
        args = self.post_parser.parse_args()
        vcName = args["vcName"]
        userName = args["userName"]
        database = args["database"]
        templateName = args["templateName"]

        if database == "master":
            if AuthorizationManager.HasAccess(userName, ResourceType.Cluster,
                                              "", Permission.Admin):
                scope = "master"
            else:
                return "access denied", 403
        elif database == "vc":
            if AuthorizationManager.HasAccess(userName, ResourceType.VC, vcName,
                                              Permission.Admin):
                scope = "vc:" + vcName
            else:
                return "access denied", 403
        else:
            scope = "user:" + userName
        template_json = request.json

        if template_json is None:
            return jsonify(result=False, message="Invalid JSON")

        dataHandler = DataHandler()
        ret = {}
        ret["result"] = dataHandler.UpdateTemplate(templateName, scope,
                                                   json.dumps(template_json))
        dataHandler.Close()
        return jsonify(ret)

    def delete(self):
        args = self.delete_parser.parse_args()
        vcName = args["vcName"]
        userName = args["userName"]
        database = args["database"]
        templateName = args["templateName"]

        if database == "master":
            if AuthorizationManager.HasAccess(userName, ResourceType.Cluster,
                                              "", Permission.Admin):
                scope = "master"
            else:
                return "access denied", 403
        elif database == "vc":
            if AuthorizationManager.HasAccess(userName, ResourceType.VC, vcName,
                                              Permission.Admin):
                scope = "vc:" + vcName
            else:
                return "access denied", 403
        else:
            scope = "user:" + userName

        dataHandler = DataHandler()
        ret = {}
        ret["result"] = dataHandler.DeleteTemplate(templateName, scope)
        dataHandler.Close()
        return jsonify(ret)


@api.resource("/jobs/priorities")
class JobPriority(Resource):
    def __init__(self):
        self.post_parser = reqparse.RequestParser()
        self.post_parser.add_argument("userName", required=True)

    def get(self):
        job_priorites = JobRestAPIUtils.get_job_priorities()
        return jsonify(job_priorites)

    def post(self):
        args = self.post_parser.parse_args()
        username = args["userName"]

        payload = request.get_json(silent=True)
        resp, status_code = JobRestAPIUtils.update_job_priorites(
            username, payload)

        if status_code != 200:
            return resp, status_code

        # Only return job_priorities affected in the POST request
        job_priorities = {}
        for job_id, _ in list(payload.items()):
            if job_id in resp:
                job_priorities[job_id] = resp[job_id]
            else:
                job_priorities[job_id] = JobRestAPIUtils.DEFAULT_JOB_PRIORITY

        return jsonify(job_priorities)


@api.resource("/JobMaxTime")
class JobMaxTime(Resource):
    def __init__(self):
        self.post_parser = reqparse.RequestParser()
        self.post_parser.add_argument("userName", required=True)
        self.post_parser.add_argument("jobId", required=True)
        self.post_parser.add_argument("second", type=int, required=True)

    def post(self):
        args = self.post_parser.parse_args()
        username = args["userName"]
        job_id = args["jobId"]
        second = args["second"]

        return JobRestAPIUtils.set_job_max_time(username, job_id, second)


@api.resource("/Insight")
class Insight(Resource):
    def __init__(self):
        self.get_parser = reqparse.RequestParser()
        self.get_parser.add_argument("jobId", required=True)
        self.get_parser.add_argument("userName", required=True)

        self.post_parser = reqparse.RequestParser()
        self.post_parser.add_argument("jobId", required=True)
        self.post_parser.add_argument("userName", required=True)

    def get(self):
        args = self.get_parser.parse_args()
        job_id = args.get("jobId")
        username = args.get("userName")

        resp, status_code = JobRestAPIUtils.get_job_insight(job_id, username)
        if status_code != 200:
            return resp, status_code
        return jsonify(resp)

    def post(self):
        args = self.post_parser.parse_args()
        job_id = args.get("jobId")
        username = args.get("userName")
        payload = request.get_json(force=True, silent=True)

        resp, status_code = JobRestAPIUtils.set_job_insight(
            job_id, username, payload)
        if status_code != 200:
            return resp, status_code
        return jsonify(resp)


@api.resource("/RepairMessage")
class RepairMessage(Resource):
    def __init__(self):
        self.post_parser = reqparse.RequestParser()
        self.post_parser.add_argument("jobId", required=True)
        self.post_parser.add_argument("userName", required=True)

    def post(self):
        args = self.post_parser.parse_args()
        job_id = args.get("jobId")
        username = args.get("userName")
        payload = request.get_json(force=True, silent=True)
        return JobRestAPIUtils.set_repair_message(username, job_id, payload)


@api.resource("/AllowRecord")
class AllowRecord(Resource):
    def __init__(self):
        self.get_parser = reqparse.RequestParser()
        self.get_parser.add_argument("userName", required=True)
        self.get_parser.add_argument("user", required=True)

        self.post_parser = reqparse.RequestParser()
        self.post_parser.add_argument("userName", required=True)
        self.post_parser.add_argument("user", required=True)
        self.post_parser.add_argument("ip", required=True)

        self.delete_parser = reqparse.RequestParser()
        self.delete_parser.add_argument("userName", required=True)
        self.delete_parser.add_argument("user", required=True)

    def get(self):
        args = self.get_parser.parse_args()
        username = args.get("userName")
        user = args.get("user")
        resp, code = JobRestAPIUtils.get_allow_record(username, user)
        return resp, code

    def post(self):
        args = self.post_parser.parse_args()
        username = args.get("userName")
        user = args.get("user")
        ip = args.get("ip")
        resp, code = JobRestAPIUtils.add_allow_record(username, user, ip)
        return resp, code

    def delete(self):
        args = self.delete_parser.parse_args()
        username = args.get("userName")
        user = args.get("user")
        resp, code = JobRestAPIUtils.delete_allow_record(username, user)
        return resp, code


@app.route("/metrics")
def metrics():
    return Response(prometheus_client.generate_latest(),
                    mimetype=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", threaded=True)
