import sys
from datetime import datetime
import utils
import yaml
from jinja2 import Environment, FileSystemLoader, Template
import base64
import tempfile

if __name__ == "__main__":
	config = { 'cluster_name': 'CI' + datetime.today().strftime("%m%d%H%M") }
	utils.render_template("template/config.yaml.template", "config.yaml",config)