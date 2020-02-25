# Job spec to  Restfulapi

We use yaml format because it allow commenting each field. We will comment about if the field is required
or optional, and gives example whenever possible.

The yaml format is only for demostration purpose, we use json actually, so all keys are snake case.

All fields are string unless specified otherwise.


```yaml
version: 2 # required, int
user:
  email: xxx@microsoft.com # required
  vc_name: xxx # required
job:
  name: 'some name or even description' # required. At most 1024 characters
  options: # optional
    dlts: # reserved by dlts platform
      debug: True # output rich debug info about job
    priority: 100 # optional, int, default to 100
    family_token: xxx # optional
    is_host_network: False # optional, bool, default to False
    is_host_ipc: False # optional, bool, default to False
    is_privileged: False # optional, bool, default to False
    is_preemptable: False # optional, bool, default to False
    default_password: password # optional, default to cluster config
    dns_policy: Default # optional, one of Default, ClusterFirstWithHostNet, ClusterFirst, default to Default
    envs: # optional
      key1: val1
      key2: val2
    ssh_public_keys: # optional, these will be appended to /home/alias/.ssh/authorized_keys
    - xxxxx
    - yyyyy
    - zzzzz
    job_path: relative/path/from/your/nfs/home
    work_path: relative/path/from/your/nfs/home
    data_path: relative/path/from/your/nfs/home
    plugins:
      image_pull: # optional
      - registry: docker.io # required
        username: xxx # required
        password: yyy # required
      blobfuse: # optional
      - account_name: account_name # required
        account_key: xxx # required
        container_name: /container_name # required
        mount_path: /tmp/blob # required
        mount_options: "-o attr_timeout=240 -o entry_timeout=240" # optional
  roles: # required
    master: # roles are defined by a map, with role name key and role definition, fields comments see below
      replicas: 1
      xxxx: yyyy
    worker: # [a-zA-Z][a-zA-Z0-9_-]{31}
      replicas: 2 # required, int
      image: ubuntu:18.04 # required
      completion_policy:
        min_failed_task_count: 1 # optional, int, can only be 1 currently. Consider this job failed when num of task from this role failed
        min_succeeded_task_count: 1 # optional, int, can only be 1 currently. Consider this job failed when num of task from this role failed
      resource:
        require: # these will be set as resource limitation used by docker container
          cpu: 200 # optional, default to cluster config
          memory_mb: 3000 # optional, int, default to cluster config
          gpu: 4 # optional, int, default to 0
      cmd: text_that_be_interpreted_by_bash # required
```

Restfulapi will validate each field, and return 400 http code when validation fails. Restfulapi Will return
uuid if job submission is successful.
