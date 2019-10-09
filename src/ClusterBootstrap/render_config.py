import sys
from datetime import datetime
import utils
import yaml
from jinja2 import Environment, FileSystemLoader, Template
import base64
import tempfile

if __name__ == "__main__":
	outbound_ip = utils.exec_cmd_local('curl ifconfig.me')
	config = { 'cluster_name': 'CI' + datetime.today().strftime("%m%d%H%M"), 'devbox_ip': outbound_ip }
	utils.render_template("template/" + sys.argv[1] + "_config.yaml.template", "config.yaml",config)