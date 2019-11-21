#!/usr/bin/python3
import os
import sys
import yaml
import utils
import argparse
import textwrap
from params import default_config_parameters
sys.path.append("../utils")
from ConfigUtils import *
from DockerUtils import push_one_docker, build_dockers, push_dockers, run_docker, find_dockers, build_docker_fullname, copy_from_docker_image, configuration

def generate_ip_from_cluster(cluster_ip_range, index ):
	slash_pos = cluster_ip_range.find("/")
	ips = cluster_ip_range if slash_pos < 0 else cluster_ip_range[:slash_pos]
	ips3 = ips[:ips.rfind(".")]
	return ips3 + "." + str(index)

def generate_trusted_domains(network_config, start_idx ):
	ret = ""
	domain = fetch_dictionary(network_config, ["domain"])
	if not (domain is None):
		ret += "DNS.%d = %s\n" % (start_idx, "*." + domain)
		start_idx +=1
	trusted_domains = fetch_dictionary(network_config, ["trusted-domains"])
	if not trusted_domains is None:
		for domain in trusted_domains:
			# "*." is encoded in domain for those entry
			ret += "DNS.%d = %s\n" % (start_idx, domain)
			start_idx +=1
	return ret

def get_platform_script_directory( target ):
	targetdir = target+"/"
	if target is None or target=="default":
		targetdir = "./"
	return targetdir
default_config_mapping = {
	"dockerprefix": (["cluster_name"], lambda x:x.lower()+"/"),
	"infrastructure-dockerregistry": (["dockerregistry"], lambda x:x),#keep
	"worker-dockerregistry": (["dockerregistry"], lambda x:x),#keep
	"api-server-ip": (["service_cluster_ip_range"], lambda x: generate_ip_from_cluster(x, 1) ),
	"dns-server-ip": (["service_cluster_ip_range"], lambda x: generate_ip_from_cluster(x, 53) ),
	"network-trusted-domains": (["network"], lambda x: generate_trusted_domains(x, 5 )),
	#master deployment scripts
	"premasterdeploymentscript" : (["platform-scripts"], lambda x: get_platform_script_directory(x)+"pre-master-deploy.sh"),
	"postmasterdeploymentscript" : (["platform-scripts"], lambda x: get_platform_script_directory(x)+"post-master-deploy.sh"),
	"mastercleanupscript" : (["platform-scripts"], lambda x: get_platform_script_directory(x)+"cleanup-master.sh"),
	"masterdeploymentlist" : (["platform-scripts"], lambda x: get_platform_script_directory(x)+"deploy.list"),
	#worker deployment scripts
	"preworkerdeploymentscript" : (["platform-scripts"], lambda x: get_platform_script_directory(x)+"pre-worker-deploy.sh"),
	"postworkerdeploymentscript" : (["platform-scripts"], lambda x: get_platform_script_directory(x)+"post-worker-deploy.sh"),
	"workercleanupscript" : (["platform-scripts"], lambda x: get_platform_script_directory(x)+"cleanup-worker.sh"),
	"workerdeploymentlist" : (["platform-scripts"], lambda x: get_platform_script_directory(x)+"deploy.list"),
	}

def load_az_params_as_default(config):
	from az_params import default_az_parameters
	# need az_params default, in case we don't have the key in config.yaml
	default_cfg = { k: v for k, v in default_az_parameters.items() }
	azure_cluster_cfg = { k: v for k, v in config["azure_cluster"].items() } if "azure_cluster" in config else {}
	merge_config(config["azure_cluster"], default_cfg["azure_cluster"])
	merge_config(config["azure_cluster"], azure_cluster_cfg)
	domain_mapping = {"regular":"%s.cloudapp.azure.com" % config["azure_cluster"]["azure_location"], "low": config.get("network_domain",config["azure_cluster"]["default_low_priority_domain"])}
	config["network"] = {"domain": domain_mapping[config["priority"]]}
	complementary_config = os.path.join(dirpath,"complementary.yaml")
	return config

def on_premise_params(config):
	print("Warning: remember to set parameters:\ngpu_count_per_node, gpu_type, worker_node_num\n when using on premise machine!")

def load_platform_type(config):
	platform_type = list(set(config.keys()) & set(config["supported_platform"]))
	assert len(platform_type) == 1 and "platform type should be specified explicitly and unique!"
	platform_type = platform_type[0]
	config["platform_type"] = platform_type
	return config

def gen_platform_wise_config(config):
	config = load_platform_type(config)
	azdefault = { 'network_domain':"config['network']['domain']", 
		'worker_node_num':"config['azure_cluster']['worker_node_num']", 
		'gpu_count_per_node':'config["sku_mapping"].get(config["azure_cluster"]["worker_vm_size"],config["sku_mapping"]["default"])["gpu-count"]',
		'gpu_type':'config["sku_mapping"].get(config["azure_cluster"]["worker_vm_size"],config["sku_mapping"]["default"])["gpu-type"]',
		'etcd_node_num': "config['azure_cluster']['infra_node_num']" }
	on_premise_default = {'network_domain':"config['network']['domain']"}
	platform_dict = { 'azure_cluster': azdefault, 'onpremise': on_premise_default }
	platform_func = { 'azure_cluster': load_az_params_as_default, 'onpremise': on_premise_params } 
	default_dict, default_func = platform_dict[config["platform_type"]], platform_func[config["platform_type"]]
	config = default_func(config)
	need_val = ['network_domain', 'worker_node_num', 'gpu_count_per_node', 'gpu_type']
	config['etcd_node_num'] = config.get('etcd_node_num')
	for ky in need_val:
		if ky not in config:
			config[ky] = eval(default_dict[ky])
	return config

def update_docker_image_config(config):
	if config["kube_custom_scheduler"] or config["kube_custom_cri"]:
		if "container" not in config["dockers"]:
			config["dockers"]["container"] = {}
		if "hyperkube" not in config["dockers"]["container"]:
			config["dockers"]["container"]["hyperkube"] = {}
	return config

def add_ssh_key(config):
	keys = fetch_config(config, ["sshKeys"])
	if isinstance( keys, list ):
		if "sshkey" in config and "sshKeys" in config and not (config["sshkey"] in config["sshKeys"]):
			config["sshKeys"].append(config["sshkey"])
	elif "sshkey" in config:
		config["sshKeys"] = []
		config["sshKeys"].append(config["sshkey"])
	return config

def get_ssh_config(config):
	# print(len(config.keys()))
	if "ssh_cert" not in config and os.path.isfile("./deploy/sshkey/id_rsa"):
		config["ssh_cert"] = "./deploy/sshkey/id_rsa"
	if "ssh_cert" in config:
		config["ssh_cert"] = expand_path(config["ssh_cert"])
	config["etcd_user"] = config["admin_username"]
	config["nfs_user"] = config["admin_username"]
	config["kubernetes_master_ssh_user"] = config["admin_username"]
	config = add_ssh_key(config)
	return config

def get_domain(config):
    if "network" in config and "domain" in config["network"] and len(config["network"]["domain"]) > 0 :
        domain = "."+config["network"]["domain"]
    else:
        domain = ""
    return domain

def get_nodes_from_config(machinerole, config):
	if "machines" not in config:
		return []
	else:
		domain = get_domain(config)
		Nodes = []
		for nodename in config["machines"]:
			nodeInfo = config["machines"][nodename]
			if "role" in nodeInfo and nodeInfo["role"]==machinerole:
				if len(nodename.split("."))<3:
					Nodes.append(nodename+domain)
				else:
					Nodes.append(nodename)
		return sorted(Nodes)

def load_node_list_by_role_from_config(config, roles):
	Nodes = []
	for role in roles:
		role = "infra" if role == "infrastructure" else role
		temp_nodes = []
		temp_nodes = get_nodes_from_config(role, config)
		if role == "infra":
			config["etcd_node"] = temp_nodes
			config["kubernetes_master_node"] = temp_nodes
		config["{}_node".format(role)] = temp_nodes
		Nodes += temp_nodes
	return Nodes

# Get the list of nodes for a particular service	
def get_node_lists_for_service(service, config):
	if "etcd_node" not in config or "worker_node" not in config:
		print("cluster not ready! nodes unknown!")
	labels = fetch_config(config, ["kubelabels"])
	nodetype = labels[service] if service in labels else labels["default"]
	if nodetype == "worker_node":
		nodes = config["worker_node"]
	elif nodetype == "etcd_node":
		nodes = config["etcd_node"]
	elif nodetype.find( "etcd_node_" )>=0:
		nodenumber = int(nodetype[nodetype.find( "etcd_node_" )+len("etcd_node_"):])
		if len(config["etcd_node"])>=nodenumber:
			nodes = [ config["etcd_node"][nodenumber-1] ]
		else:
			nodes = []
	elif nodetype == "all":
		nodes = config["worker_node"] + config["etcd_node"]
	else:
		machines = fetch_config(config, ["machines"])
		if machines is None:
			print ("Service %s has a nodes type %s, but there is no machine configuration to identify node" % (service, nodetype))
			exit(-1)
		allnodes = config["worker_node"] + config["etcd_node"]
		nodes = []
		for node in allnodes:
			nodename = kubernetes_get_node_name(node)
			if nodename in machines and nodetype in machines[nodename]:
				nodes.append(node)
	return nodes

def update_config(config):
	apply_config_mapping(config, default_config_mapping)
	config["webportal_node"] = None if len(get_node_lists_for_service("webportal", config))==0 \
								else get_node_lists_for_service("webportal", config)[0]
	if ("influxdb_node" not in config):
	    config["influxdb_node"] = config["webportal_node"]
	if ("elasticsearch_node" not in config):
	    config["elasticsearch_node"] = config["webportal_node"]
	if ("mysql_node" not in config):
	    config["mysql_node"] = None if len(get_node_lists_for_service("mysql", config))==0 \
								else get_node_lists_for_service("mysql", config)[0]
	if ("host" not in config["prometheus"]):
	    config["prometheus"]["host"] = None if len(get_node_lists_for_service("prometheus", config))==0 \
	    								else get_node_lists_for_service("prometheus", config)[0]
	config = update_docker_image_config(config)
	return config

def load_config(args):
	config = init_config(default_config_parameters)
	if args.verbose:
		utils.verbose = True
		print("Args = {0}".format(args))

	# we care about "action to apply this time", so we don't load cluster.yaml, which reflect the accumualted status
	for cnf_fn in args.config:
		config_file = os.path.join(dirpath, cnf_fn)
		if not os.path.exists(config_file):
			parser.print_help()
			print("ERROR: {} does not exist!".format(config_file))
			exit()
		with open(config_file) as cf:
			merge_config(config, yaml.safe_load(cf))

	load_node_list_by_role_from_config(config, ['infra', 'worker', 'nfs'])
	config = gen_platform_wise_config(config)

	if os.path.exists("./deploy/clusterID.yml"):
		f = open("./deploy/clusterID.yml")
		tmp = yaml.load(f)
		f.close()
		if "clusterId" in tmp:
			config["clusterId"] = tmp["clusterId"]
		config = update_config(config)
	else:
		apply_config_mapping(config, default_config_mapping)
		config = update_docker_image_config(config)

	config = get_ssh_config(config)
	configuration( config, args.verbose )

	if args.verbose:
		print("deploy " + command + " " + (" ".join(args.nargs)))
		print("PlatformScripts = {0}".format(config["platform-scripts"]))

	return config

def run_command(args, command, parser):
	config = load_config(args)

if __name__ == '__main__':
	# the program always run at the current directory.
	dirpath = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))
	os.chdir(dirpath)
	parser = argparse.ArgumentParser( prog='cloud_init_deploy.py',
		formatter_class=argparse.RawDescriptionHelpFormatter,
		description=textwrap.dedent('''
		Build, deploy and administer a DL workspace cluster.

		Prerequest:
		* Create config.yaml according to instruction in docs/deployment/Configuration.md.
		* Metadata of deployed cluster is stored at deploy.

		Command:
			render	render all files from template
	''') )
	parser.add_argument("-y", "--yes",
		help="Answer yes automatically for all prompt",
		action="store_true" )
	parser.add_argument("--force",
		help="Force perform certain operation",
		action="store_true" )
	parser.add_argument("--native",
		help="Run docker in native mode (in how it is built)",
		action="store_true" )
	parser.add_argument("-s", "--sudo",
		help = "Execute scripts in sudo",
		action="store_true" )
	parser.add_argument("-v", "--verbose",
		help = "verbose print",
		action="store_true")
	parser.add_argument("--nocache",
		help = "Build docker without cache",
		action="store_true")
	parser.add_argument("--nodes",
		help = "Specify an python regular expression that limit the nodes that the operation is applied.",
		action="store",
		default=None
		)
	parser.add_argument('-cnf','--config', nargs='+', help='Specify the config files you want to load', 
		default = ["config.yaml", "complementary.yaml"])
	parser.add_argument("command",
		help = "See above for the list of valid command" )
	parser.add_argument('nargs', nargs=argparse.REMAINDER,
		help="Additional command argument",
		)
	args = parser.parse_args()
	command = args.command
	nargs = args.nargs
	if args.verbose:
		utils.verbose = True
	if args.nodes is not None:
		limitnodes = args.nodes

	if not os.path.exists("./deploy"):
		os.system("mkdir -p ./deploy")

	if command == "scriptblocks":
		if nargs[0] in scriptblocks:
			run_script_blocks( args.verbose, scriptblocks[nargs[0]])
		else:
			parser.print_help()
			print ("Error: Unknown scriptblocks " + nargs[0])
	else:
		run_command(args, command, parser)