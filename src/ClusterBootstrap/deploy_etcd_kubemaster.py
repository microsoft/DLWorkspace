import json
import os
import time
import argparse
import uuid
import subprocess
import sys

import yaml
from jinja2 import Environment, FileSystemLoader, Template
import base64

def render(template_file, target_file):
	template = ENV.get_template(os.path.abspath(template_file))
	content = template.render(cnf=config)
	with open(target_file, 'w') as f:
	    f.write(content)


def SSH_exec_cmd(identity_file, user,host,cmd):
	print ('ssh -i %s "%s@%s" "%s"' % (identity_file, user, host, cmd) )
	os.system('ssh -i %s "%s@%s" "%s"' % (identity_file, user, host, cmd) )


def scp (identity_file, source, target, user, host):
	os.system('scp -i %s -r "%s" "%s@%s:%s"' % (identity_file, source, user, host, target) )

f = open(os.path.join(os.path.dirname(os.path.realpath(__file__)),"config.yaml"))
config = yaml.load(f)

print "==============================================="
print "generating configuration files..."
deployDirs = ["web/deploy/etcd","web/deploy/kubelet","web/deploy/master"]
for deployDir in deployDirs:
	if not os.path.exists(deployDir):
	    os.system("mkdir -p %s" % (deployDir))


renderfiles = []

kubemaster_cfg_files = [f for f in os.listdir("./web/template/etcd") if os.path.isfile(os.path.join("./web/template/etcd", f))]
for file in kubemaster_cfg_files:
	renderfiles.append((os.path.join("./web/template/etcd", file),os.path.join("./web/deploy/etcd", file)))


kubemaster_cfg_files = [f for f in os.listdir("./web/template/master") if os.path.isfile(os.path.join("./web/template/master", f))]
for file in kubemaster_cfg_files:
	renderfiles.append((os.path.join("./web/template/master", file),os.path.join("./web/deploy/master", file)))



ENV = Environment(loader=FileSystemLoader("/"))
for (template_file,target_file) in renderfiles:
	render(template_file,target_file)

if True:
	#print "==============================================="
	#print "deploy configuration files to web server..."
	#scp(config["ssh_cert"],"./web/deploy","/var/www/html", config["webserver_user"], config["webserver"] )

	print "==============================================="
	print "deploy certificates to etcd server"
	SSH_exec_cmd (config["ssh_cert"], config["etcd_user"], config["etcd_node"], "sudo mkdir -p /etc/kubernetes/ssl") 
	SSH_exec_cmd (config["ssh_cert"], config["etcd_user"], config["etcd_node"], "sudo chown %s /etc/kubernetes/ssl " % (config["etcd_user"])) 
	scp(config["ssh_cert"],"./ssl/etcd","/etc/kubernetes/ssl", config["etcd_user"], config["etcd_node"] )

	print "==============================================="
	print "starting etcd service..."

	SSH_exec_cmd(config["ssh_cert"], config["etcd_user"], config["etcd_node"], "docker rm -f \$(docker ps -q -a)")

	scp(config["ssh_cert"],"./web/deploy/etcd/docker_etcd.sh","/home/%s/docker_etcd.sh" % config["etcd_user"], config["etcd_user"], config["etcd_node"] )
	SSH_exec_cmd(config["ssh_cert"], config["etcd_user"], config["etcd_node"], "chmod +x /home/%s/docker_etcd.sh" % config["etcd_user"])

	scp(config["ssh_cert"],"./web/deploy/etcd/docker_etcd_ssl.sh","/home/%s/docker_etcd_ssl.sh" % config["etcd_user"], config["etcd_user"], config["etcd_node"] )
	SSH_exec_cmd(config["ssh_cert"], config["etcd_user"], config["etcd_node"], "chmod +x /home/%s/docker_etcd_ssl.sh" % config["etcd_user"])


	SSH_exec_cmd(config["ssh_cert"], config["etcd_user"], config["etcd_node"], "/home/%s/docker_etcd_ssl.sh" % config["etcd_user"])

	print "==============================================="
	print "init etcd service..."
	time.sleep(5)
	scp(config["ssh_cert"],"./web/deploy/etcd/init_network.sh","/home/%s/init_network.sh" % config["etcd_user"], config["etcd_user"], config["etcd_node"] )
	SSH_exec_cmd(config["ssh_cert"], config["etcd_user"], config["etcd_node"], "chmod +x /home/%s/init_network.sh" % config["etcd_user"])
	SSH_exec_cmd(config["ssh_cert"], config["etcd_user"], config["etcd_node"], "/home/%s/init_network.sh" % config["etcd_user"])


print "==============================================="
print "starting kubernetes master ..."
SSH_exec_cmd(config["ssh_cert"], config["kubernetes_master_ssh_user"], config["kubernetes_master_node"], "sudo mkdir -p /etc/kubernetes")
SSH_exec_cmd(config["ssh_cert"], config["kubernetes_master_ssh_user"], config["kubernetes_master_node"], "sudo mkdir -p /etc/systemd/system/flanneld.service.d")
SSH_exec_cmd(config["ssh_cert"], config["kubernetes_master_ssh_user"], config["kubernetes_master_node"], "sudo mkdir -p /etc/systemd/system/docker.service.d")
SSH_exec_cmd(config["ssh_cert"], config["kubernetes_master_ssh_user"], config["kubernetes_master_node"], "sudo mkdir -p /etc/flannel")
SSH_exec_cmd(config["ssh_cert"], config["kubernetes_master_ssh_user"], config["kubernetes_master_node"], "sudo mkdir -p /etc/kubernetes/manifests")

SSH_exec_cmd(config["ssh_cert"], config["kubernetes_master_ssh_user"], config["kubernetes_master_node"], "sudo chown -R %s /etc/kubernetes" % config["kubernetes_master_ssh_user"])
SSH_exec_cmd(config["ssh_cert"], config["kubernetes_master_ssh_user"], config["kubernetes_master_node"], "sudo chown -R %s /etc/flannel" % config["kubernetes_master_ssh_user"])

scp(config["ssh_cert"],"./ssl/apiserver","/etc/kubernetes/ssl", config["kubernetes_master_ssh_user"], config["kubernetes_master_node"] )


scp(config["ssh_cert"],"./ssl/apiserver","/home/%s/" % config["kubernetes_master_ssh_user"], config["kubernetes_master_ssh_user"], config["kubernetes_master_node"] )
SSH_exec_cmd(config["ssh_cert"], config["kubernetes_master_ssh_user"], config["kubernetes_master_node"], "sudo mkdir -p /etc/ssl/etcd")
SSH_exec_cmd(config["ssh_cert"], config["kubernetes_master_ssh_user"], config["kubernetes_master_node"], "sudo mv /home/%s/apiserver/* /etc/ssl/etcd/" % (config["kubernetes_master_ssh_user"]))


scp(config["ssh_cert"],"./web/deploy/master/basicauth","/etc/kubernetes/", config["kubernetes_master_ssh_user"], config["kubernetes_master_node"] )



scp(config["ssh_cert"],"./web/deploy/master/40-ExecStartPre-symlink.conf","/home/%s/40-ExecStartPre-symlink.conf" % config["kubernetes_master_ssh_user"], config["kubernetes_master_ssh_user"], config["kubernetes_master_node"] )
SSH_exec_cmd(config["ssh_cert"], config["kubernetes_master_ssh_user"], config["kubernetes_master_node"], "sudo mv /home/%s/40-ExecStartPre-symlink.conf /etc/systemd/system/flanneld.service.d/40-ExecStartPre-symlink.conf" % (config["kubernetes_master_ssh_user"]))


scp(config["ssh_cert"],"./web/deploy/master/40-flannel.conf","/home/%s/40-flannel.conf" % config["kubernetes_master_ssh_user"], config["kubernetes_master_ssh_user"], config["kubernetes_master_node"] )
SSH_exec_cmd(config["ssh_cert"], config["kubernetes_master_ssh_user"], config["kubernetes_master_node"], "sudo mv /home/%s/40-flannel.conf /etc/systemd/system/docker.service.d/40-flannel.conf" % (config["kubernetes_master_ssh_user"]))


scp(config["ssh_cert"],"./web/deploy/master/kubelet.service","/home/%s/kubelet.service" % config["kubernetes_master_ssh_user"] , config["kubernetes_master_ssh_user"], config["kubernetes_master_node"] )
SSH_exec_cmd(config["ssh_cert"], config["kubernetes_master_ssh_user"], config["kubernetes_master_node"], "sudo mv /home/%s/kubelet.service /etc/systemd/system/kubelet.service" % (config["kubernetes_master_ssh_user"]))


scp(config["ssh_cert"],"./web/deploy/master/options.env","/home/%s/options.env" % config["kubernetes_master_ssh_user"] , config["kubernetes_master_ssh_user"], config["kubernetes_master_node"] )
SSH_exec_cmd(config["ssh_cert"], config["kubernetes_master_ssh_user"], config["kubernetes_master_node"], "sudo mv /home/%s/options.env /etc/flannel/options.env" % (config["kubernetes_master_ssh_user"]))

filelist = ["kube-proxy.yaml","kube-apiserver.yaml", "kube-controller-manager.yaml", "kube-scheduler.yaml"]
for file in filelist:
	scp(config["ssh_cert"],"./web/deploy/master/"+file,"/etc/kubernetes/manifests/"+file, config["kubernetes_master_ssh_user"], config["kubernetes_master_node"] )


SSH_exec_cmd(config["ssh_cert"], config["kubernetes_master_ssh_user"], config["kubernetes_master_node"], "sudo mkdir -p /opt/bin")
SSH_exec_cmd(config["ssh_cert"], config["kubernetes_master_ssh_user"], config["kubernetes_master_node"], "sudo chown -R %s /opt/bin" % config["kubernetes_master_ssh_user"])
scp(config["ssh_cert"],config["kubelet_bin"],"/opt/bin", config["kubernetes_master_ssh_user"], config["kubernetes_master_node"] )


exec_cmd_list = ["sudo systemctl daemon-reload","sudo systemctl stop flanneld","sudo systemctl stop kubelet","sudo systemctl start flanneld", "sudo systemctl stop docker", "sudo systemctl start docker", "sudo systemctl start kubelet", "sudo systemctl start rpc-statd", "sudo systemctl enable flanneld", "sudo systemctl enable kubelet"]
for exec_cmd in exec_cmd_list:
	SSH_exec_cmd(config["ssh_cert"], config["kubernetes_master_ssh_user"], config["kubernetes_master_node"], exec_cmd)