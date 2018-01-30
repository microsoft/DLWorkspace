# Job Families

Suppose your job needs to launch another job (e.g. a library you want to use must launch docker containers), or to kill a job which had been created. To allow this, DLWorkspace provides a RESTful API at `$DLWS_REST_API/child`, where `$DLWS_REST_API` is an environment variable passed in to every job. This document describes that API, and gives an example of how to use it in continuation passing style.

### Family Token

To make sure no malicious requests are made, DLWS passes every job a unique ID in the `$FAMILY_TOKEN` environment variable, which is used for authentication. Every request to the `/child` API must provide the query parameter `familyToken=$FAMILY_TOKEN`.

### Submitting Jobs

The path to submit a job is `$DLWS_REST_API/child/SubmitJob`. As mentioned prior, the family token must be passed as a query parameter, and the newly made job will be given this same token. The userName and userId parameters will be inherited from the submitter job, but all other parameters work the same as a normally submitted job.

The body of the response will be JSON, and will either contain an error message at the key `error` or the jobId at the key `jobId`. This is the same as the normal API.

Here is an example of how to submit a child job from within a python script: 

```python
def submit_child(error_handler, succes_handler):
    import os
    import requests

    jobSettings = {
        "resourcegpu": 0,
        "jobName": "tensorflow-ipython-cpu",
        "dataPath": "imagenet",
        "image": "tensorflow/tensorflow:latest",
        "cmd": "export HOME=/job && jupyter notebook --no-browser --port=8888 --ip=0.0.0.0 --notebook-dir=/",
        "interactivePort": "8888",
        "jobType": "training",
        "jobtrainingtype": "RegularJob",
        "runningasroot": "0",
        "familyToken": os.environ["FAMILY_TOKEN"]
    }

    api_url = os.environ["DLWS_REST_API"] + "/child"
    submit_child_resp = requests.get(api_url + "/SubmitJob", params=jobSettings, timeout=3)
    submit_child_resp.raise_for_status()
    submit_child_resp = submit_child_resp.json()
    if "error" in submit_child_resp:
        error_handler(submit_child_resp["error"])
    else:
        succes_handler(submit_child_resp["jobId"])
```

**Note: If a job submitted by a user is killed, all jobs submitted by that original job will also be killed.**

### Killing jobs

To kill a job, just pass the job-to-be-killed's id and the current job's familyToken to `$DLWS_REST_API/child/KillJob`. The response body will be json and have a single string at the key result, which is either "Success, the job is scheduled to be terminated." or "Cannot Kill the job. Job ID: $jobId" where $jobId denotes the id of the job which failed to be killed.

```python
def kill_job(jobId, error_handler, succes_handler):
    import os
    import requests
  
    api_url = os.environ["DLWS_REST_API"]
    family_token = os.environ["FAMILY_TOKEN"]

    submit_child_resp = requests.get(api_url + "KillJob", timeout=3,
                                     params=dict(familyToken=family_token, jobId=jobId))
    submit_child_resp.raise_for_status()
    submit_child_resp = submit_child_resp.json()
    result = submit_child_resp["result"]
    if "Success" not in submit_child_resp:
        succes_handler()
    else:
        error_handler(jobId)
```

### Getting the detail of a job

TODO: Explain what a job detail is

The api takes the current job's familyToken and the jobId of the job whose detail is requested, and returns that job's detail in JSON as an object. It can be accessed at `$DLWS_REST_API/child/JobDetail`.

```python
def job_detail(jobId, succes_handler):
    import os
    import requests
  
    api_url = os.environ["DLWS_REST_API"]
    family_token = os.environ["FAMILY_TOKEN"]

    submit_child_resp = requests.get(api_url + "JobDetail", timeout=3,
                                     params=dict(familyToken=family_token, jobId=jobId))
    submit_child_resp.raise_for_status()
    detail = submit_child_resp.json()
    succes_handler(detail)
```

### Getting the IP of a job

TODO: Check the accuracy of this section w.r.t. networking

DLWorkspace supports [kubernetes networking](https://kubernetes.io/docs/concepts/cluster-administration/networking/), which means each job has its own virtual IP. A running job can access this IP by giving its familyToken and that job's id to `$DLWS_REST_API/child/GetJobIP`. The response body will be json of either the form `{"error": "Could not find job with id $jobId"}` or `{"IP": $jobIP}`, where $jobId and $jobIP are respectively the ID and IP of the job whose IP was supposed to have been gotten.

```python
def job_ip(jobId, succes_handler, error_handler):
    import os
    import requests
  
    api_url = os.environ["DLWS_REST_API"]
    family_token = os.environ["FAMILY_TOKEN"]

    submit_child_resp = requests.get(api_url + "GetJobIP", timeout=3,
                                     params=dict(familyToken=family_token, jobId=jobId))
    submit_child_resp.raise_for_status()
    submit_child_resp = submit_child_resp.json()
	if "error" in submit_child_resp:
		error_handler(jobId)
	else:
		succes_handler(submit_child_resp["IP"])
```
