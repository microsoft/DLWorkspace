
#!/usr/bin/python 
import json
import os
import time
import datetime
import argparse
import uuid
import subprocess
import sys
import textwrap
import re
import math
import distutils.dir_util
import distutils.file_util
import shutil

import yaml
from jinja2 import Environment, FileSystemLoader, Template
import base64

from shutil import copyfile,copytree
import urllib
import socket


import utils


def gen_ETCD_certificates():

	config["etcd_ssl_dns"] = ""
	config["etcd_ssl_ip"] = "IP.1 = 127.0.0.1\n" + "\n".join(["IP."+str(i+2)+" = "+ip for i,ip in enumerate(config["etcd_node"])])
	renderfiles = []
	utils.render_template_directory("./template/ssl", "./deploy/ssl",config)


	os.system("cd ./deploy/ssl && bash ./gencerts_etcd.sh")	


def deploy_ETCD_docker():
	
	etcd_servers = config["etcd_node"]
	etcd_server_user = config["etcd_user"]
	config["discovery_url"] = utils.get_ETCD_discovery_URL(len(config["etcd_node"]))


	utils.render_template_directory("./template/etcd", "./deploy/etcd",config)

	for etcd_server_address in etcd_servers:
		#print "==============================================="
		#print "deploy configuration files to web server..."
		#scp(config["ssh_cert"],"./deploy","/var/www/html", config["webserver_user"], config["webserver"] )

		print "==============================================="
		print "deploy certificates to etcd server %s" % etcd_server_address


		utils.SSH_exec_cmd (config["ssh_cert"], etcd_server_user, etcd_server_address, "sudo mkdir -p /etc/etcd/ssl ; sudo chown %s /etc/etcd/ssl " % (etcd_server_user)) 
		utils.scp(config["ssh_cert"],"./deploy/ssl/etcd/ca.pem","/etc/etcd/ssl", etcd_server_user, etcd_server_address )
		utils.scp(config["ssh_cert"],"./deploy/ssl/etcd/etcd.pem","/etc/etcd/ssl", etcd_server_user, etcd_server_address )
		utils.scp(config["ssh_cert"],"./deploy/ssl/etcd/etcd-key.pem","/etc/etcd/ssl", etcd_server_user, etcd_server_address )

		print "==============================================="
		print "starting etcd service on %s ..." % etcd_server_address


		config["etcd_node_ip"] = etcd_server_address
		utils.render_template("./template/etcd/docker_etcd_ssl.sh","./deploy/etcd/docker_etcd_ssl.sh",config)
		utils.scp(config["ssh_cert"],"./deploy/etcd/docker_etcd_ssl.sh","/home/%s/docker_etcd_ssl.sh" % etcd_server_user, etcd_server_user, etcd_server_address )
		utils.SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_server_address, "chmod +x /home/%s/docker_etcd_ssl.sh ; /home/%s/docker_etcd_ssl.sh" % (etcd_server_user,etcd_server_user))




if __name__ == '__main__':
	config = {}
	config["etcd_user"] = "core"
	config["etcd_node"] = ["10.177.92.20","10.177.92.21","10.177.92.22"]
	config["ssh_cert"] = "~/.ssh/id_rsa"
	
	gen_ETCD_certificates()
	deploy_ETCD_docker()