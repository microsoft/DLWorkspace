#!/usr/bin/env python3
import os
import sys
import json
import re


def gen_grafana_config(data):
    # Remove inputs and requires
    data.pop("__inputs", None)
    data.pop("__requires", None)

    # Set datasource to None in templating
    templating = data.get("templating")
    if templating is not None:
        for l in templating.get("list", []):
            if "datasource" in l:
                l["datasource"] = None

    for panel in data.get("panels"):
        # Set datasource to None
        if "datasource" in panel:
            panel["datasource"] = None

        # Replace {{ with {{'{{'}} and }} with {{'}}'}} in legendFormat
        for target in panel.get("targets", []):
            legend_format = target.get("legendFormat")
            if legend_format is None:
                continue
            target["legendFormat"] = re.sub("{{([^}]*)}}",
                                            "{{'{{'}}\\1{{'}}'}}",
                                            legend_format)

    uid = data.get("uid")
    title = data.get("title")
    if title is not None and uid != title.replace(" ", "-").lower():
        uid = title.replace(" ", "-").lower()
    if uid is not None:
        data["uid"] = uid

    return {"dashboard": data}


if __name__ == "__main__":
    input_file = sys.argv[1]
    output_dir = sys.argv[2]
    output_file = os.path.join(output_dir, os.path.basename(input_file))

    with open(input_file) as f:
        data = json.load(f)

    config = gen_grafana_config(data)

    with open(output_file, 'w') as f:
        json.dump(config, f, indent=2)

