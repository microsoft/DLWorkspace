#!/usr/bin/env python3

from jinja2 import Environment, FileSystemLoader


def GenTensorboardMeta(jobParams, serviceTemplate, tensorboardAppTemplate):
    ENV = Environment(loader=FileSystemLoader("/"))
    jobParams["svc-name"] = "tensorboard-" + jobParams["id"]
    jobParams["app-name"] = "tensorboard-" + jobParams["id"]
    jobParams["port"] = "6006"
    jobParams["port-name"] = "tensorboard"
    jobParams["port-type"] = "TCP"
    jobParams["tensorboard-id"] = "tensorboard-" + jobParams["id"]

    template = ENV.get_template(serviceTemplate)

    tensorboardMeta = template.render(svc=jobParams)

    tensorboardMeta += "\n---\n"

    template = ENV.get_template(tensorboardAppTemplate)
    tensorboardMeta += template.render(job=jobParams)

    #print "tensorboard is running at: https://dlws-master/api/v1/proxy/namespaces/default/services/%s:tensorboard " % jobParams["svc-name"]
    return tensorboardMeta
