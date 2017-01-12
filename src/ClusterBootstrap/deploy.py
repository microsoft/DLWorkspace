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

from shutil import copyfile,copytree
import urllib



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


def Get_ETCD_DiscoveryURL(size):
        try:
            output = urllib.urlopen("https://discovery.etcd.io/new?size=%d" % size ).read()
            if not "https://discovery.etcd.io" in output:
            	raise Exception("ERROR: we cannot get etcd discovery url from 'https://discovery.etcd.io/new?size=%d', got message %s" % (size,output)) 
        except Exception as e:
        	raise Exception("ERROR: we cannot get etcd discovery url from 'https://discovery.etcd.io/new?size=%d'" % size) 
        return output

def _Check_Config_Items(cnfitem, cnf):
    if not cnfitem in cnf:
        raise Exception("ERROR: we cannot find %s in config file" % cnfitem) 
    else:
        print "Checking configurations '%s' = '%s'" % (cnfitem, cnf[cnfitem])
 
def Check_Config(cnf):
    _Check_Config_Items("discovery_url",cnf)
    _Check_Config_Items("webserver",cnf)
    _Check_Config_Items("kubernetes_master_node",cnf)
    _Check_Config_Items("kubernetes_master_ssh_user",cnf)
    _Check_Config_Items("api_serviers",cnf)
    _Check_Config_Items("etcd_user",cnf)
    _Check_Config_Items("etcd_node",cnf)
    _Check_Config_Items("etcd_endpoints",cnf)
    _Check_Config_Items("ssh_cert",cnf)
    _Check_Config_Items("pod_ip_range",cnf)
    _Check_Config_Items("basic_auth",cnf)
    _Check_Config_Items("kubernetes_docker_image",cnf)
    _Check_Config_Items("service_cluster_ip_range",cnf)
    _Check_Config_Items("webserver_docker_image",cnf)
    _Check_Config_Items("pxe_docker_image",cnf)
    if not os.isfile(config["ssh_cert"]):
    	raise Exception("ERROR: we cannot find ssh key file at %s. \n please run 'python build-pxe-coreos.py docker_image_name' to generate ssh key file and pxe server image." % config["ssh_cert"]) 

if __name__ == '__main__':
    f = open(os.path.join(os.path.dirname(os.path.realpath(__file__)),"config.yaml"))
    config = yaml.load(f)
    f.close()

    print "==============================================="
    print "generating configuration files..."
    os.system("rm -r ./deploy/bin")
    os.system("rm -r ./deploy/etcd")
    os.system("rm -r ./deploy/kube-addons")
    os.system("rm -r ./deploy/kubelet")
    os.system("rm -r ./deploy/master")

    deployDirs = ["deploy/etcd","deploy/kubelet","deploy/master","deploy/web-docker/kubelet","deploy/kube-addons","deploy/bin"]
    for deployDir in deployDirs:
	    if not os.path.exists(deployDir):
	        os.system("mkdir -p %s" % (deployDir))


    etcd_servers = [x.strip() for x in config["etcd_node"].strip().split(",") if len(x.strip())>0]
    etcd_server_user = config["etcd_user"]

    if len(etcd_servers) <= 0:
        raise Exception("ERROR: we need at least one etcd_server.") 

    kubernetes_masters = [x.strip() for x in config["kubernetes_master_node"].strip().split(",") if len(x.strip())>0]
    kubernetes_master_user = config["kubernetes_master_ssh_user"]

    if len(kubernetes_masters) <= 0:
        raise Exception("ERROR: we need at least one etcd_server.") 


    config["webserver"] = etcd_servers[0]
    config["discovery_url"] = Get_ETCD_DiscoveryURL(len(etcd_servers))

    if "ssh_cert" not in config and os.isfile("./sshkey/id_rsa"):
    	config["ssh_cert"] = "./sshkey/id_rsa"
    	config["etcd_user"] = "core"
    	config["kubernetes_master_ssh_user"] = "core"

	f = open(config["ssh_cert"])
	sshkey_public = f.read()
	f.close()

	config["sshkey"] = sshkey_public
    Check_Config(config)


    renderfiles = []

    kubemaster_cfg_files = [f for f in os.listdir("./template/etcd") if os.path.isfile(os.path.join("./template/etcd", f))]
    for file in kubemaster_cfg_files:
	    renderfiles.append((os.path.join("./template/etcd", file),os.path.join("./deploy/etcd", file)))


    kubemaster_cfg_files = [f for f in os.listdir("./template/master") if os.path.isfile(os.path.join("./template/master", f))]
    for file in kubemaster_cfg_files:
	    renderfiles.append((os.path.join("./template/master", file),os.path.join("./deploy/master", file)))


    kubemaster_cfg_files = [f for f in os.listdir("./template/web-docker") if os.path.isfile(os.path.join("./template/web-docker", f))]
    for file in kubemaster_cfg_files:
	    renderfiles.append((os.path.join("./template/web-docker", file),os.path.join("./deploy/web-docker", file)))


    kubemaster_cfg_files = [f for f in os.listdir("./template/kubelet") if os.path.isfile(os.path.join("./template/kubelet", f))]
    for file in kubemaster_cfg_files:
	    renderfiles.append((os.path.join("./template/kubelet", file),os.path.join("./deploy/web-docker/kubelet", file)))


    kubemaster_cfg_files = [f for f in os.listdir("./template/kube-addons") if os.path.isfile(os.path.join("./template/kube-addons", f))]
    for file in kubemaster_cfg_files:
	    renderfiles.append((os.path.join("./template/kube-addons", file),os.path.join("./deploy/kube-addons", file)))


    renderfiles.append(("pxe-kubelet/www/pxe-coreos-kube.yml.template","pxe-kubelet/www/pxe-coreos-kube.yml"))

    ENV = Environment(loader=FileSystemLoader("/"))
    for (template_file,target_file) in renderfiles:
	    render(template_file,target_file)




    for kubernetes_master in kubernetes_masters:
	    print "==============================================="
	    print "Clean up kubernetes master %s... (It is OK to see 'Errors' in this section)" % kubernetes_master


	    exec_cmd_list = ["sudo systemctl stop flanneld","sudo systemctl stop kubelet", "sudo systemctl stop docker"]
	    for exec_cmd in exec_cmd_list:
		    SSH_exec_cmd(config["ssh_cert"], kubernetes_master_user, kubernetes_master, exec_cmd)

	    SSH_exec_cmd(config["ssh_cert"], kubernetes_master_user, kubernetes_master, "sudo rm -r /etc/kubernetes")
	    SSH_exec_cmd(config["ssh_cert"], kubernetes_master_user, kubernetes_master, "sudo rm -r /etc/ssl/etcd")
	    SSH_exec_cmd(config["ssh_cert"], kubernetes_master_user, kubernetes_master, "sudo rm -r /etc/systemd/system/flanneld.service.d")
	    SSH_exec_cmd(config["ssh_cert"], kubernetes_master_user, kubernetes_master, "sudo rm -r /etc/systemd/system/docker.service.d")
	    SSH_exec_cmd(config["ssh_cert"], kubernetes_master_user, kubernetes_master, "sudo rm -r /etc/flannel")
	    SSH_exec_cmd(config["ssh_cert"], kubernetes_master_user, kubernetes_master, "sudo rm -r /etc/ssl/etcd")

    for etcd_server_address in etcd_servers:
	    print "==============================================="
	    print "Clean up etcd servers %s... (It is OK to see 'Errors' in this section)" % etcd_server_address    	
	    SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_server_address, "docker rm -f \$(docker ps -q -a)")
	    SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_server_address, "sudo rm -r /var/etcd/data")
	    SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_server_address, "sudo rm -r /etc/kubernetes")



    for etcd_server_address in etcd_servers:
	    #print "==============================================="
	    #print "deploy configuration files to web server..."
	    #scp(config["ssh_cert"],"./deploy","/var/www/html", config["webserver_user"], config["webserver"] )

	    print "==============================================="
	    print "deploy certificates to etcd server %s" % etcd_server_address
        
	    SSH_exec_cmd (config["ssh_cert"], etcd_server_user, etcd_server_address, "sudo mkdir -p /etc/kubernetes/ssl") 
	    SSH_exec_cmd (config["ssh_cert"], etcd_server_user, etcd_server_address, "sudo chown %s /etc/kubernetes/ssl " % (etcd_server_user)) 
	    scp(config["ssh_cert"],"./ssl/etcd","/etc/kubernetes/ssl", etcd_server_user, etcd_server_address )

	    print "==============================================="
	    print "starting etcd service on %s ..." % etcd_server_address



	    scp(config["ssh_cert"],"./deploy/etcd/docker_etcd.sh","/home/%s/docker_etcd.sh" % etcd_server_user, etcd_server_user, etcd_server_address )
	    SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_server_address, "chmod +x /home/%s/docker_etcd.sh" % etcd_server_user)

	    scp(config["ssh_cert"],"./deploy/etcd/docker_etcd_ssl.sh","/home/%s/docker_etcd_ssl.sh" % etcd_server_user, etcd_server_user, etcd_server_address )
	    SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_server_address, "chmod +x /home/%s/docker_etcd_ssl.sh" % etcd_server_user)


	    SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_server_address, "/home/%s/docker_etcd_ssl.sh" % etcd_server_user)




    print "==============================================="
    print "init etcd service on %s ..."  % etcd_servers[0]
    time.sleep(30)
    #TODO: Wait until etcd service is launched. 
    scp(config["ssh_cert"],"./deploy/etcd/init_network.sh","/home/%s/init_network.sh" % etcd_server_user, etcd_server_user, etcd_server_address )
    SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_servers[0], "chmod +x /home/%s/init_network.sh" % etcd_server_user)
    SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_servers[0], "/home/%s/init_network.sh" % etcd_server_user)


    for kubernetes_master in kubernetes_masters:
	    print "==============================================="
	    print "starting kubernetes master on %s..." % kubernetes_master

	    SSH_exec_cmd(config["ssh_cert"], kubernetes_master_user, kubernetes_master, "sudo mkdir -p /etc/kubernetes")
	    SSH_exec_cmd(config["ssh_cert"], kubernetes_master_user, kubernetes_master, "sudo mkdir -p /etc/systemd/system/flanneld.service.d")
	    SSH_exec_cmd(config["ssh_cert"], kubernetes_master_user, kubernetes_master, "sudo mkdir -p /etc/systemd/system/docker.service.d")
	    SSH_exec_cmd(config["ssh_cert"], kubernetes_master_user, kubernetes_master, "sudo mkdir -p /etc/flannel")
	    SSH_exec_cmd(config["ssh_cert"], kubernetes_master_user, kubernetes_master, "sudo mkdir -p /etc/kubernetes/manifests")

	    SSH_exec_cmd(config["ssh_cert"], kubernetes_master_user, kubernetes_master, "sudo chown -R %s /etc/kubernetes" % kubernetes_master_user)
	    SSH_exec_cmd(config["ssh_cert"], kubernetes_master_user, kubernetes_master, "sudo chown -R %s /etc/flannel" % kubernetes_master_user)

	    scp(config["ssh_cert"],"./ssl/apiserver","/etc/kubernetes/ssl", kubernetes_master_user, kubernetes_master )


	    scp(config["ssh_cert"],"./ssl/apiserver","/home/%s/" % kubernetes_master_user, kubernetes_master_user, kubernetes_master )
	    SSH_exec_cmd(config["ssh_cert"], kubernetes_master_user, kubernetes_master, "sudo mkdir -p /etc/ssl/etcd")
	    SSH_exec_cmd(config["ssh_cert"], kubernetes_master_user, kubernetes_master, "sudo mv /home/%s/apiserver/* /etc/ssl/etcd/" % (kubernetes_master_user))


	    scp(config["ssh_cert"],"./deploy/master/basicauth","/etc/kubernetes/", kubernetes_master_user, kubernetes_master )



	    scp(config["ssh_cert"],"./deploy/master/40-ExecStartPre-symlink.conf","/home/%s/40-ExecStartPre-symlink.conf" % kubernetes_master_user, kubernetes_master_user, kubernetes_master )
	    SSH_exec_cmd(config["ssh_cert"], kubernetes_master_user, kubernetes_master, "sudo mv /home/%s/40-ExecStartPre-symlink.conf /etc/systemd/system/flanneld.service.d/40-ExecStartPre-symlink.conf" % (kubernetes_master_user))


	    scp(config["ssh_cert"],"./deploy/master/40-flannel.conf","/home/%s/40-flannel.conf" % kubernetes_master_user, kubernetes_master_user, kubernetes_master )
	    SSH_exec_cmd(config["ssh_cert"], kubernetes_master_user, kubernetes_master, "sudo mv /home/%s/40-flannel.conf /etc/systemd/system/docker.service.d/40-flannel.conf" % (kubernetes_master_user))


	    scp(config["ssh_cert"],"./deploy/master/kubelet.service","/home/%s/kubelet.service" % kubernetes_master_user , kubernetes_master_user, kubernetes_master )
	    SSH_exec_cmd(config["ssh_cert"], kubernetes_master_user, kubernetes_master, "sudo mv /home/%s/kubelet.service /etc/systemd/system/kubelet.service" % (kubernetes_master_user))


	    scp(config["ssh_cert"],"./deploy/master/options.env","/home/%s/options.env" % kubernetes_master_user , kubernetes_master_user, kubernetes_master )
	    SSH_exec_cmd(config["ssh_cert"], kubernetes_master_user, kubernetes_master, "sudo mv /home/%s/options.env /etc/flannel/options.env" % (kubernetes_master_user))

	    filelist = ["kube-proxy.yaml","kube-apiserver.yaml", "kube-controller-manager.yaml", "kube-scheduler.yaml"]
	    for file in filelist:
		    scp(config["ssh_cert"],"./deploy/master/"+file,"/etc/kubernetes/manifests/"+file, kubernetes_master_user, kubernetes_master )


	    SSH_exec_cmd(config["ssh_cert"], kubernetes_master_user, kubernetes_master, "sudo mkdir -p /opt/bin")
	    SSH_exec_cmd(config["ssh_cert"], kubernetes_master_user, kubernetes_master, "sudo chown -R %s /opt/bin" % kubernetes_master_user)
	
	    urllib.urlretrieve ("http://ccsdatarepo.westus.cloudapp.azure.com/data/kube/kubelet/kubelet", "./deploy/bin/kubelet")
	    urllib.urlretrieve ("http://ccsdatarepo.westus.cloudapp.azure.com/data/kube/kubelet/kubectl", "./deploy/bin/kubectl")


	    scp(config["ssh_cert"],"./deploy/bin/kubelet","/opt/bin", kubernetes_master_user, kubernetes_master )
	    scp(config["ssh_cert"],"./deploy/bin/kubectl","/opt/bin", kubernetes_master_user, kubernetes_master )

	    SSH_exec_cmd(config["ssh_cert"], kubernetes_master_user, kubernetes_master, "sudo chmod +x /opt/bin/*")

	    SSH_exec_cmd(config["ssh_cert"], kubernetes_master_user, kubernetes_master, "sudo mkdir -p /opt/addons")
	    SSH_exec_cmd(config["ssh_cert"], kubernetes_master_user, kubernetes_master, "sudo chown -R %s /opt/addons" % kubernetes_master_user)
	    scp(config["ssh_cert"],"./deploy/kube-addons","/opt/addons", kubernetes_master_user, kubernetes_master )


	    exec_cmd_list = ["sudo systemctl daemon-reload","sudo systemctl stop flanneld","sudo systemctl stop kubelet","sudo systemctl start flanneld", "sudo systemctl stop docker", "sudo systemctl start docker", "sudo systemctl start kubelet", "sudo systemctl start rpc-statd", "sudo systemctl enable flanneld", "sudo systemctl enable kubelet"]
	    for exec_cmd in exec_cmd_list:
		    SSH_exec_cmd(config["ssh_cert"], kubernetes_master_user, kubernetes_master, exec_cmd)



    print "==============================================="
    print "generating kubelet configuration files ..."

    copyfile("./deploy/bin/kubelet","./deploy/web-docker/kubelet/kubelet")
    copytree("certificate-service","./deploy/web-docker/certificate-service")
    copytree("./ssl/ca","./deploy/web-docker/certificate-service/ca")


    exec_cmd = "docker build -t %s pxe-kubelet/" % config["pxe_docker_image"]
    os.system(exec_cmd)

    exec_cmd = "docker push %s" % config["pxe_docker_image"]
    os.system(exec_cmd)


    exec_cmd = "docker build -t %s deploy/web-docker/" % config["webserver_docker_image"]
    os.system(exec_cmd)

    exec_cmd = "docker push %s" % config["webserver_docker_image"]
    os.system(exec_cmd)

    exec_cmd = "docker run -d -p 80:80 -p 5000:5000 %s" % config["webserver_docker_image"]
    SSH_exec_cmd(config["ssh_cert"], etcd_server_user, etcd_server_address, exec_cmd)