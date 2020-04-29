#!/usr/bin/env python3

import os
import sys
import yaml

headers = """
groups:
  - name: kill-idle
    rules:
"""

kill_template = """
    - alert: kill-idle-jobs-email-%s
      for: %dh
      expr: avg(task_gpu_percent{vc_name="%s"}) by (user_email, job_name, vc_name) == 0
      labels:
        type: kill_idle_job_email
    - alert: kill-idle-jobs-%s
      for: %dh
      expr: avg(task_gpu_percent{vc_name="%s"}) by (user_email, job_name, vc_name) == 0
      labels:
        type: reaper
"""


def config_kill_rule(m):
    for vc_name, hour in m.items():
        print(kill_template % (vc_name, hour, vc_name, vc_name, hour, vc_name))


def extract_relevant_config(config_map):
    return config_map.get("prometheus", {}).get("alerting",
                                                {}).get("kill-idle", {})


if __name__ == "__main__":
    with open(sys.argv[1]) as f:
        config = yaml.full_load(f.read())

    print(headers)
    config_kill_rule(extract_relevant_config(config))
