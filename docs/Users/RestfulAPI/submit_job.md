# Use DLWorkspace API to submit job 

This document descripts how to submit a job via dlworkspace restfulapi. 

To submit a job, you need to get the following information

* API endpoints: http://[Webportal domain name]/api/dlws/postJob
* Authentication: Email and Key, which you can get by click your username on the DLworkspace portal (upper right corner)

### Submitting Jobs


```python
def submit_job():
    import requests

    jobparams = """
        {
        "jobName":"caffe-ssh",
        "resourcegpu":0,
        "workPath":"./",
        "dataPath":"imagenet",
        "jobPath":"",
        "image":"bvlc/caffe:cpu",
        "cmd":"echo $HOME",
        "interactivePort":"22",
        "runningasroot":true,
        "env":[],
        "jobtrainingtype":"RegularJob"
        }
        """
    payload = {}
    payload["Json"] = jobparams
    r = requests.post('http://hongzltest-infra01.westus2.cloudapp.azure.com/api/dlws/postJob?Email=[your-email]&Key=[your-key]', data=payload)
    print (r.text)
```

