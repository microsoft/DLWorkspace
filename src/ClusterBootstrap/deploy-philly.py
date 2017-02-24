
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


def check_etcd_service():
	print "waiting for ETCD service is ready..."
	etcd_servers = config["etcd_node"]
	cmd = "curl --cacert %s --cert %s --key %s 'https://%s:2379/v2/keys'" % ("./deploy/ssl/etcd/ca.pem","./deploy/ssl/etcd/etcd.pem","./deploy/ssl/etcd/etcd-key.pem", etcd_servers[0])
	while os.system(cmd) != 0:
		time.sleep(5)
	print "ETCD service is ready to use..."



def deploy_master(kubernetes_master):
		print "==============================================="
		kubernetes_master_user = config["kubernetes_master_ssh_user"]
		print "starting kubernetes master on %s..." % kubernetes_master

		config["master_ip"] = kubernetes_master
		utils.render_template("./template/master/kube-apiserver.yaml","./deploy/master/kube-apiserver.yaml",config)
		utils.render_template("./template/master/kubelet.service","./deploy/master/kubelet.service",config)
		utils.render_template("./template/master/pre-master-deploy.sh","./deploy/master/pre-master-deploy.sh",config)
		utils.render_template("./template/master/post-master-deploy.sh","./deploy/master/post-master-deploy.sh",config)


		utils.SSH_exec_script(config["ssh_cert"],kubernetes_master_user, kubernetes_master, "./deploy/master/philly-pre-master-deploy.sh")


		with open("./deploy/master/philly-deploy.list","r") as f:
			deploy_files = [s.split(",") for s in f.readlines() if len(s.split(",")) == 2]
		for (source, target) in deploy_files:
			if (os.path.isfile(source.strip()) or os.path.exists(source.strip())):
				utils.sudo_scp(config["ssh_cert"],source.strip(),target.strip(),kubernetes_master_user,kubernetes_master)


		utils.SSH_exec_script(config["ssh_cert"],kubernetes_master_user, kubernetes_master, "./deploy/master/philly-post-master-deploy.sh")

def deploy_masters():

	print "==============================================="
	print "Prepare to deploy kubernetes master"
	print "waiting for ETCD service is ready..."
	check_etcd_service()
	print "==============================================="
	print "Generating master configuration files..."

	kubernetes_masters = config["kubernetes_master_node"]
	kubernetes_master_user = config["kubernetes_master_ssh_user"]

	utils.render_template_directory("./template/master", "./deploy/master",config)
	utils.render_template_directory("./template/kube-addons", "./deploy/kube-addons",config)


	urllib.urlretrieve ("http://ccsdatarepo.westus.cloudapp.azure.com/data/kube/kubelet/kubelet", "./deploy/bin/kubelet")
	urllib.urlretrieve ("http://ccsdatarepo.westus.cloudapp.azure.com/data/kube/kubelet/kubectl", "./deploy/bin/kubectl")
	

	for i,kubernetes_master in enumerate(kubernetes_masters):
		deploy_master(kubernetes_master)


	#utils.SSH_exec_cmd(config["ssh_cert"], kubernetes_master_user, kubernetes_masters[0], "until curl -q http://127.0.0.1:8080/version/ ; do sleep 5; echo 'waiting for master...'; done;  sudo /opt/bin/kubectl create -f /opt/addons/kube-addons/", False)





if __name__ == '__main__':
	# the program always run at the current directory. 
	dirpath = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))
	# print "Directory: " + dirpath
	os.chdir(dirpath)


	config = {}
	config_file = os.path.join(dirpath,"config.yaml")
	# print "Config file: " + config_file
	if not os.path.exists(config_file):
		parser.print_help()
		print "ERROR: config.yaml does not exist!"
		exit()
	
	f = open(config_file)
	config.update(yaml.load(f))
	f.close()


	config["etcd_user"] = "core"
	config["kubernetes_master_ssh_user"] = "core"
	config["etcd_node"] = ["10.177.92.20","10.177.92.21","10.177.92.22"]
	config["kubernetes_master_node"] = ["10.177.92.23"]
	config["ssh_cert"] = "./id_rsa"
	config["api_serviers"] = "https://"+config["kubernetes_master_node"][0]
	config["etcd_endpoints"] = ",".join(["https://"+x+":2379" for x in config["etcd_node"]])

	gen_ETCD_certificates()
	deploy_ETCD_docker()
	deploy_masters()