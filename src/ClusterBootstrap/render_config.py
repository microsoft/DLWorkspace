import sys
from datetime import datetime
import utils
import yaml
from jinja2 import Environment, FileSystemLoader, Template
import base64
import tempfile

if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[2] == "wide":
        devbox_ips = ["131.107.0.0/16", "167.220.0.0/16"]
    else:
        # devbox outbound_ip
        devbox_ips = ["{}/32".format(utils.exec_cmd_local('curl ifconfig.me'))]
    config = {'cluster_name': 'ci' + datetime.today().strftime("%m%d%H%M"),
              'devbox_ips': devbox_ips}
    utils.render_template(
        "template/" + sys.argv[1] + "_config.yaml.template", "config.yaml", config)
