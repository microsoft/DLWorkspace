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


def generate_response(result):
    resp = jsonify(result)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["dataType"] = "json"
    return resp


class PostJob(Resource):
    def post(self):
        params = request.get_json(force=True)
        logger.info("Post Job")
        logger.info(params)

        ret = {}
        output = JobRestAPIUtils.SubmitJob(json.dumps(params))

        if "jobId" in output:
            ret["jobId"] = output["jobId"]
        else:
            if "error" in output:
                ret["error"] = "Cannot create job!" + output["error"]
            else:
                ret["error"] = "Cannot create job!"

        logger.info("Submit job through restapi, output is %s, ret is %s",
                    output, ret)
        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"
        return resp


api.add_resource(PostJob, "/PostJob")


class ListJobs(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("userName")
        parser.add_argument("vcName")
        parser.add_argument("jobOwner")
        parser.add_argument("num")
        args = parser.parse_args()
        username = args["userName"]
        vc_name = args["vcName"]
        job_owner = args["jobOwner"]
        num = None
        if args["num"] is not None:
            try:
                num = int(args["num"])
            except:
                # Set default number of inactive jobs to 20
                num = 20
                pass
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
                    pass

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
        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"
        return resp


api.add_resource(ListJobs, "/ListJobs")


class ListJobsV2(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("userName")
        parser.add_argument("vcName")
        parser.add_argument("jobOwner")
        parser.add_argument("num")
        args = parser.parse_args()
        username = args["userName"]
        vc_name = args["vcName"]
        job_owner = args["jobOwner"]
        num = None
        if args["num"] is not None:
            try:
                num = int(args["num"])
            except:
                # Set default number of inactive jobs to 20
                num = 20
                pass

        jobs = JobRestAPIUtils.get_job_list_v2(username, vc_name, job_owner,
                                               num)

        for _, job_list in jobs.items():
            if isinstance(job_list, list):
                for job in job_list:
                    remove_creds(job)

        resp = generate_response(jobs)
        return resp


api.add_resource(ListJobsV2, "/ListJobsV2")


class KillJob(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("jobId")
        parser.add_argument("userName")
        args = parser.parse_args()
        job_id = args["jobId"]
        username = args["userName"]
        result = JobRestAPIUtils.kill_job(username, job_id)
        ret = {}
        if result:
            # NOTE "Success" prefix is used in reaper, please also update reaper code
            # if need to change it.
            ret["result"] = "Success, the job is scheduled to be terminated."
        else:
            ret["result"] = "Cannot Kill the job. Job ID:" + job_id

        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp


api.add_resource(KillJob, "/KillJob")


class PauseJob(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("jobId")
        parser.add_argument("userName")
        args = parser.parse_args()
        job_id = args["jobId"]
        username = args["userName"]
        result = JobRestAPIUtils.pause_job(username, job_id)
        ret = {}
        if result:
            ret["result"] = "Success, the job is scheduled to be paused."
        else:
            ret["result"] = "Cannot pause the job. Job ID:" + job_id

        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp


api.add_resource(PauseJob, "/PauseJob")


class ResumeJob(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("jobId")
        parser.add_argument("userName")
        args = parser.parse_args()
        job_id = args["jobId"]
        username = args["userName"]
        result = JobRestAPIUtils.resume_job(username, job_id)
        ret = {}
        if result:
            ret["result"] = "Success, the job is scheduled to be resumed."
        else:
            ret["result"] = "Cannot resume the job. Job ID:" + job_id

        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp


api.add_resource(ResumeJob, "/ResumeJob")


class ApproveJob(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("jobId")
        parser.add_argument("userName")
        args = parser.parse_args()
        job_id = args["jobId"]
        username = args["userName"]
        result = JobRestAPIUtils.approve_job(username, job_id)
        ret = {}
        if result:
            ret["result"] = "Success, the job has been approved."
        else:
            ret["result"] = "Cannot approve the job. Job ID:" + job_id

        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp


api.add_resource(ApproveJob, "/ApproveJob")


class KillJobs(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("jobIds")
        parser.add_argument("userName")
        args = parser.parse_args()
        job_ids = args["jobIds"]
        username = args["userName"]
        result = JobRestAPIUtils.kill_jobs(username, job_ids)
        ret = {"result": result}

        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp


api.add_resource(KillJobs, "/KillJobs")


class PauseJobs(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("jobIds")
        parser.add_argument("userName")
        args = parser.parse_args()
        job_ids = args["jobIds"]
        username = args["userName"]
        result = JobRestAPIUtils.pause_jobs(username, job_ids)
        ret = {"result": result}

        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp


api.add_resource(PauseJobs, "/PauseJobs")


class ResumeJobs(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("jobIds")
        parser.add_argument("userName")
        args = parser.parse_args()
        job_ids = args["jobIds"]
        username = args["userName"]
        result = JobRestAPIUtils.resume_jobs(username, job_ids)
        ret = {"result": result}

        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp


api.add_resource(ResumeJobs, "/ResumeJobs")


class ApproveJobs(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("jobIds")
        parser.add_argument("userName")
        args = parser.parse_args()
        job_ids = args["jobIds"]
        username = args["userName"]
        result = JobRestAPIUtils.approve_jobs(username, job_ids)
        ret = {"result": result}

        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp


api.add_resource(ApproveJobs, "/ApproveJobs")

# FIXME JobRestAPIUtils.CloneJob is not implemented
# class CloneJob(Resource):
#     def get(self):
#         parser = reqparse.RequestParser()
#         parser.add_argument("jobId")
#         parser.add_argument("userName")
#         args = parser.parse_args()
#         jobId = args["jobId"]
#         userName = args["userName"]
#         result = JobRestAPIUtils.CloneJob(userName, jobId)
#         ret = {}
#         if result:
#             ret["result"] = "Success, the job is scheduled to be cloned."
#         else:
#             ret["result"] = "Cannot clone the job. Job ID:" + jobId
#
#         resp = jsonify(ret)
#         resp.headers["Access-Control-Allow-Origin"] = "*"
#         resp.headers["dataType"] = "json"
#
#         return resp

# api.add_resource(CloneJob, "/CloneJob")


class GetJobDetail(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("jobId")
        parser.add_argument("userName")
        args = parser.parse_args()
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

        resp = jsonify(job)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"
        return resp


api.add_resource(GetJobDetail, "/GetJobDetail")


class GetJobDetailV2(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("jobId")
        parser.add_argument("userName")
        args = parser.parse_args()
        jobId = args["jobId"]
        userName = args["userName"]
        job = JobRestAPIUtils.GetJobDetailV2(userName, jobId)
        remove_creds(job)
        resp = generate_response(job)
        return resp


api.add_resource(GetJobDetailV2, "/GetJobDetailV2")


class GetJobLog(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("jobId", required=True)
        parser.add_argument("userName", required=True)
        parser.add_argument("cursor")
        args = parser.parse_args()
        jobId = args["jobId"]
        userName = args["userName"]
        cursor = args["cursor"]
        return JobRestAPIUtils.GetJobLog(userName, jobId, cursor)


api.add_resource(GetJobLog, "/GetJobLog")


class GetJobStatus(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("jobId")
        args = parser.parse_args()
        jobId = args["jobId"]
        job = JobRestAPIUtils.GetJobStatus(jobId)
        resp = jsonify(job)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp


api.add_resource(GetJobStatus, "/GetJobStatus")


class GetClusterStatus(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("userName")
        args = parser.parse_args()
        userName = args["userName"]
        cluster_status, last_updated_time = JobRestAPIUtils.GetClusterStatus()
        cluster_status["last_updated_time"] = last_updated_time
        resp = jsonify(cluster_status)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp


api.add_resource(GetClusterStatus, "/GetClusterStatus")


class AddUser(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("userName")
        parser.add_argument("uid")
        parser.add_argument("gid")
        parser.add_argument("groups")
        args = parser.parse_args()

        ret = {}
        userName = args["userName"]
        if args["uid"] is None or len(args["uid"].strip()) == 0:
            uid = authorization.INVALID_ID
        else:
            uid = args["uid"]

        if args["gid"] is None or len(args["gid"].strip()) == 0:
            gid = authorization.INVALID_ID
        else:
            gid = args["gid"]

        if args["groups"] is None or len(args["groups"].strip()) == 0:
            groups = []
        else:
            groups = args["groups"]

        ret["status"] = JobRestAPIUtils.AddUser(userName, uid, gid, groups)
        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp


api.add_resource(AddUser, "/AddUser")


class GetAllUsers(Resource):
    def get(self):
        data_handler = None
        try:
            data_handler = DataHandler()
            ret = data_handler.GetUsers()
            resp = jsonify(ret)
            resp.headers["Access-Control-Allow-Origin"] = "*"
            resp.headers["dataType"] = "json"
            return resp
        except Exception as e:
            return "Internal Server Error. " + str(e), 400
        finally:
            if data_handler is not None:
                data_handler.Close()


api.add_resource(GetAllUsers, "/GetAllUsers")


class UpdateAce(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("userName")
        parser.add_argument("identityName")
        parser.add_argument("resourceType")
        parser.add_argument("resourceName")
        parser.add_argument("permissions")
        args = parser.parse_args()
        username = args["userName"]
        identityName = str(args["identityName"])
        resourceType = int(args["resourceType"])
        resourceName = str(args["resourceName"])
        permissions = int(args["permissions"])
        ret = {}
        ret["result"] = JobRestAPIUtils.UpdateAce(username, identityName,
                                                  resourceType, resourceName,
                                                  permissions)
        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp


api.add_resource(UpdateAce, "/UpdateAce")


class DeleteAce(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("userName")
        parser.add_argument("identityName")
        parser.add_argument("resourceType")
        parser.add_argument("resourceName")
        args = parser.parse_args()
        username = args["userName"]
        identityName = str(args["identityName"])
        resourceType = int(args["resourceType"])
        resourceName = str(args["resourceName"])
        ret = {}
        ret["result"] = JobRestAPIUtils.DeleteAce(username, identityName,
                                                  resourceType, resourceName)
        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp


api.add_resource(DeleteAce, "/DeleteAce")


class IsClusterAdmin(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("userName")
        args = parser.parse_args()
        username = args["userName"]
        ret = {}
        ret["result"] = AuthorizationManager.IsClusterAdmin(username)
        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp


api.add_resource(IsClusterAdmin, "/IsClusterAdmin")


class GetACL(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("userName")
        args = parser.parse_args()
        username = args["userName"]
        ret = {}
        ret["result"] = AuthorizationManager.GetAcl(username)
        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp


api.add_resource(GetACL, "/GetACL")


class GetAllACL(Resource):
    def get(self):
        ret = {}
        ret["result"] = ACLManager.GetAllAcl()
        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp


api.add_resource(GetAllACL, "/GetAllACL")


class ListVCs(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("userName")
        args = parser.parse_args()
        userName = args["userName"]
        ret = {}
        ret["result"] = JobRestAPIUtils.ListVCs(userName)

        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp


api.add_resource(ListVCs, "/ListVCs")


class GetVC(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("userName")
        parser.add_argument("vcName")
        args = parser.parse_args()
        username = args["userName"]
        vc_name = args["vcName"]
        ret = JobRestAPIUtils.get_vc(username, vc_name)

        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp


api.add_resource(GetVC, "/GetVC")


class GetVCV2(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("userName")
        parser.add_argument("vcName")
        args = parser.parse_args()
        username = args["userName"]
        vc_name = args["vcName"]
        ret = JobRestAPIUtils.get_vc_v2(username, vc_name)

        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp


api.add_resource(GetVCV2, "/GetVCV2")


class AddVC(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("vcName")
        parser.add_argument("quota")
        parser.add_argument("metadata")
        parser.add_argument("userName")
        args = parser.parse_args()
        vcName = args["vcName"]
        quota = args["quota"]
        metadata = args["metadata"]
        userName = args["userName"]
        ret = {}
        ret["result"] = JobRestAPIUtils.AddVC(userName, vcName, quota,
                                              metadata)

        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp


api.add_resource(AddVC, "/AddVC")


class DeleteVC(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("vcName")
        parser.add_argument("userName")
        args = parser.parse_args()
        vcName = args["vcName"]
        userName = args["userName"]
        ret = {}
        ret["result"] = JobRestAPIUtils.DeleteVC(userName, vcName)
        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp


api.add_resource(DeleteVC, "/DeleteVC")


class UpdateVC(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("vcName")
        parser.add_argument("quota")
        parser.add_argument("metadata")
        parser.add_argument("userName")
        args = parser.parse_args()
        vcName = args["vcName"]
        quota = args["quota"]
        metadata = args["metadata"]
        userName = args["userName"]
        ret = {}
        ret["result"] = JobRestAPIUtils.UpdateVC(userName, vcName, quota,
                                                 metadata)

        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp


api.add_resource(UpdateVC, "/UpdateVC")


class ListStorages(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("vcName")
        parser.add_argument("userName")
        args = parser.parse_args()
        vcName = args["vcName"]
        userName = args["userName"]
        ret = {}
        ret["result"] = JobRestAPIUtils.ListStorages(userName, vcName)
        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp


api.add_resource(ListStorages, "/ListStorages")


class AddStorage(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("vcName")
        parser.add_argument("storageType")
        parser.add_argument("url")
        parser.add_argument("metadata")

        parser.add_argument("defaultMountPath")
        parser.add_argument("userName")
        args = parser.parse_args()
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
        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp


api.add_resource(AddStorage, "/AddStorage")


class DeleteStorage(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("vcName")
        parser.add_argument("userName")
        parser.add_argument("url")
        args = parser.parse_args()
        vcName = args["vcName"]
        userName = args["userName"]
        url = args["url"]
        ret = {}
        ret["result"] = JobRestAPIUtils.DeleteStorage(userName, vcName, url)
        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp


api.add_resource(DeleteStorage, "/DeleteStorage")


class UpdateStorage(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("vcName")
        parser.add_argument("storageType")
        parser.add_argument("url")
        parser.add_argument("metadata")

        parser.add_argument("defaultMountPath")
        parser.add_argument("userName")
        args = parser.parse_args()
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

        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp


api.add_resource(UpdateStorage, "/UpdateStorage")


class Endpoint(Resource):
    def get(self):
        """return job["endpoints"]: curl -X GET /endpoints?jobId=...&userName=..."""
        parser = reqparse.RequestParser()
        parser.add_argument("jobId")
        parser.add_argument("userName")
        args = parser.parse_args()
        jobId = args["jobId"]
        username = args["userName"]

        ret = JobRestAPIUtils.GetEndpoints(username, jobId)

        # TODO: return 403 error code
        # Return empty list for now to keep backward compatibility with old portal.
        resp = generate_response(ret)
        return resp

    def post(self):
        """set job["endpoints"]: curl -X POST -H "Content-Type: application/json" /endpoints --data "{"jobId": ..., "endpoints": ["ssh", "ipython"] }"""
        parser = reqparse.RequestParser()
        parser.add_argument("userName")
        args = parser.parse_args()
        username = args["userName"]

        params = request.get_json(silent=True)
        job_id = params["jobId"]
        requested_endpoints = params["endpoints"]

        interactive_ports = []
        # endpoints should be ["ssh", "ipython", "tensorboard", {"name": "port name", "podPort": "port on pod in 40000-49999"}]
        for interactive_port in [
                elem for elem in requested_endpoints
                if elem not in ["ssh", "ipython", "tensorboard"]
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

        resp = generate_response(msg)
        return resp


api.add_resource(Endpoint, "/endpoints")


class Templates(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("vcName", location="args")
        parser.add_argument("userName", location="args")
        args = parser.parse_args()
        vcName = args["vcName"]
        userName = args["userName"]

        dataHandler = DataHandler()
        ret = dataHandler.GetTemplates("master") or []
        ret += dataHandler.GetTemplates("vc:" + vcName) or []
        ret += dataHandler.GetTemplates("user:" + userName) or []
        dataHandler.Close()
        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument("vcName", location="args")
        parser.add_argument("userName", location="args")
        parser.add_argument("database", location="args")
        parser.add_argument("templateName", location="args")
        args = parser.parse_args()
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
            if AuthorizationManager.HasAccess(userName, ResourceType.VC,
                                              vcName, Permission.Admin):
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
        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp

    def delete(self):
        parser = reqparse.RequestParser()
        parser.add_argument("vcName", location="args")
        parser.add_argument("userName", location="args")
        parser.add_argument("database", location="args")
        parser.add_argument("templateName", location="args")
        args = parser.parse_args()
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
            if AuthorizationManager.HasAccess(userName, ResourceType.VC,
                                              vcName, Permission.Admin):
                scope = "vc:" + vcName
            else:
                return "access denied", 403
        else:
            scope = "user:" + userName

        dataHandler = DataHandler()
        ret = {}
        ret["result"] = dataHandler.DeleteTemplate(templateName, scope)
        dataHandler.Close()
        resp = jsonify(ret)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"

        return resp


api.add_resource(Templates, "/templates")


class JobPriority(Resource):
    def get(self):
        job_priorites = JobRestAPIUtils.get_job_priorities()
        resp = jsonify(job_priorites)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"
        return resp

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument("userName", location="args")
        args = parser.parse_args()
        username = args["userName"]

        payload = request.get_json(silent=True)
        success, all_job_priorities = JobRestAPIUtils.update_job_priorites(
            username, payload)
        http_status = 200 if success else 400

        # Only return job_priorities affected in the POST request
        job_priorities = {}
        for job_id, _ in list(payload.items()):
            if job_id in all_job_priorities:
                job_priorities[job_id] = all_job_priorities[job_id]
            else:
                job_priorities[job_id] = JobRestAPIUtils.DEFAULT_JOB_PRIORITY

        resp = jsonify(job_priorities)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["dataType"] = "json"
        resp.status_code = http_status
        return resp


api.add_resource(JobPriority, "/jobs/priorities")


@app.route("/metrics")
def metrics():
    return Response(prometheus_client.generate_latest(),
                    mimetype=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", threaded=True)
