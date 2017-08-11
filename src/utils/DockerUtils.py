import os
import time
import datetime
import argparse
import uuid
import subprocess
import sys
import tempfile
import getpass
import pwd
import grp
from os.path import expanduser
from DirectoryUtils import cd

def build_docker( dockername, dirname, verbose=False, nocache=False ):
	# docker name is designed to use lower case. 
	dockername = dockername.lower()
	if verbose:
		print "Building docker ... " + dockername + " .. @" + dirname
	with cd(dirname):
		# print "Test if prebuid.sh exists"
		if os.path.exists("prebuild.sh"):
			print "Execute prebuild.sh for docker %s" % dockername
			os.system("bash prebuild.sh")
		if nocache:
			cmd = "docker build --no-cache -t "+ dockername + " ."
		else:
			cmd = "docker build -t "+ dockername + " ."
		os.system(cmd)
	return dockername
	
def push_docker( dockername, docker_register, verbose=False):
	# docker name is designed to use lower case. 
	dockername = dockername.lower()
	if verbose:
		print "Pushing docker ... " + dockername + " to " + docker_register
	cmd = "docker tag "+ dockername + " " + docker_register + dockername
	cmd += "; docker push " + docker_register + dockername
	os.system(cmd)
	return dockername
	
def run_docker(dockername, prompt="", dockerConfig = None, sudo = False, options = "" ):
	if not (dockerConfig is None):
		if "su" in dockerConfig:
			sudo = True
		if "options" in dockerConfig and len(options)<=0:
			options = dockerConfig["options"]
	uid = os.getuid()
	username = getpass.getuser()
	username = username.split()[0]
	groupid = pwd.getpwnam(username).pw_gid
	groupname = grp.getgrgid(groupid).gr_name
	groupname = groupname.split()[0]
	homedir = expanduser("~")
	currentdir = os.path.abspath(os.getcwd())
	mapVolume = "-v " + homedir + ":" + homedir
	if not (dockerConfig is None) and "workdir" in dockerConfig:
		currentdir = dockerConfig["workdir"]
		if "volumes" in dockerConfig:
			for volume,mapping in dockerConfig["volumes"].iteritems():
				if "from" in mapping and "to" in mapping:
					mapdir = os.path.abspath(mapping["from"])
					mapVolume += " -v " + mapdir + ":" + mapping["to"]
	else:
		if not (homedir in currentdir):
			mapVolume += " -v "+ currentdir + ":" + currentdir
	print "Running docker " + dockername + " as Userid: " + str(uid) + "(" + username +"), + Group:"+str(groupid) + "("+groupname+") at " + homedir
	dirname = tempfile.mkdtemp()
	wname = os.path.join(dirname,"run.sh")
	fw = open( wname, "w+" )
	fw.write("#!/bin/bash\n")
	fw.write("if [ -f /etc/lsb-release ]; then \n")
	fw.write("addgroup --force-badname --gid "+str(groupid)+" " +groupname+"\n")
	fw.write("adduser --force-badname --home " + homedir + " --shell /bin/bash --no-create-home --uid " + str(uid)+ " -gecos '' "+username+" --disabled-password --gid "+str(groupid)+"\n" )
	fw.write("adduser "+username +" sudo\n")
	fw.write("adduser "+username +" docker\n")
	fw.write("fi\n")
	fw.write("if [ -f /etc/redhat-release ]; then \n")
	fw.write("groupadd --gid "+str(groupid)+" " +groupname+"\n")
	fw.write("useradd  --home " + homedir + " --shell /bin/bash --no-create-home --uid " + str(uid)+ " "+username+" --password '' --gid "+str(groupid)+"\n" )
	fw.write("usermod -aG wheel "+username +"\n")
	fw.write("fi\n")
	fw.write("echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers\n")
	fw.write("chmod --recursive 0755 /root\n")
	# Please note: setting HOME environment in docker may nullify additional environment variables, 
	# such as GOPATH.
	fw.write("export HOME="+homedir+"\n")
	fw.write("cd "+currentdir+"\n")
	fw.write("dockerd > /dev/null 2>&1 &\n")
	fw.write("""echo "export PATH=\$PATH:\$GOPATH/bin" | cat >> /etc/bash.bashrc \n""")
	fw.write("""echo "export GOPATH=\$GOPATH" | cat >> /etc/bash.bashrc \n""")
	if not sudo:
		fw.write("su -m "+username +"\n")
	else:
		print "Run in super user mode..."
		fw.write("/bin/bash")
	fw.close()
	os.chmod(wname, 0755)
	if prompt == "":
		hostname = "Docker["+dockername+"]"
	else:
		hostname = prompt
	if homedir in currentdir:
		cmd = "docker run --privileged --hostname " + hostname + " " + options + " --rm -ti " + mapVolume + " -v "+dirname+ ":/tmp/runcommand -w "+homedir + " " + dockername + " /tmp/runcommand/run.sh"
	else:
		cmd = "docker run --privileged --hostname " + hostname + " " + options + " --rm -ti " + mapVolume + " -v "+dirname+ ":/tmp/runcommand -w "+homedir + " " + dockername + " /tmp/runcommand/run.sh"
	print "Execute: " + cmd
	os.system(cmd)
	
def find_dockers( dockername):
	print "Search for dockers .... "+dockername
	tmpf = tempfile.NamedTemporaryFile()
	tmpfname = tmpf.name; 
	tmpf.close()
	#os.remove(tmpfname)
	dockerimages_all = os.system("docker images > " + tmpfname)
	with open(tmpfname,"r") as dockerimage_file:
		lines = dockerimage_file.readlines()
	os.remove(tmpfname)
	numlines = len(lines)
	dockerdics = {}
	for i in range(1,numlines):
		imageinfo = lines[i].split()
		if imageinfo == "<none>":
			imagename = imageinfo[0]
		else:
			imagename = imageinfo[0]+":"+imageinfo[1]
		if dockername in imagename:
			dockerdics[imagename] = True
	matchdockers = dockerdics.keys()
	return matchdockers
	
def build_docker_fullname( config, dockername, verbose = False ):
	dockerprefix = config["dockerprefix"];
	dockertag = config["dockertag"]
	infra_dockers = config["infrastructure-dockers"] if "infrastructure-dockers" in config else {}
	infra_docker_registry = config["infrastructure-dockerregistry"] if "infrastructure-dockerregistry" in config else config["dockerregistry"]
	worker_docker_registry = config["worker-dockerregistry"] if "worker-dockerregistry" in config else config["dockerregistry"]
	if dockername in infra_dockers:	
		return ( infra_docker_registry + dockerprefix + dockername + ":" + dockertag ).lower()
	else:
		return ( worker_docker_registry + dockerprefix + dockername + ":" + dockertag ).lower()
	
def get_docker_list(rootdir, dockerprefix, dockertag, nargs, verbose = False ):
	docker_list = {}
	if not (nargs is None) and len(nargs)>0:
		nargs = map(lambda x:x.lower(), nargs )
	fnames = os.listdir(rootdir)
	for fname in fnames:
		if nargs is None or len(nargs)==0 or fname.lower() in nargs:
			entry = os.path.join(rootdir, fname )
			if os.path.isdir(entry):
				basename = os.path.basename(entry)
				dockername = dockerprefix + os.path.basename(entry)+":"+dockertag
				docker_list[dockername] = ( basename, entry )
	return docker_list

def build_dockers(rootdir, dockerprefix, dockertag, nargs, verbose = False, nocache = False ):
	docker_list = get_docker_list(rootdir, dockerprefix, dockertag, nargs, verbose )
	for dockername, tuple in docker_list.iteritems():
		build_docker(dockername, tuple[1], verbose, nocache = nocache )

def build_one_docker(dirname, dockerprefix, dockertag, basename, verbose = False, nocache = False):
	dockername = dockerprefix + basename + ":" + dockertag
	return build_docker( dockername, dirname, verbose = verbose, nocache = nocache)

def push_one_docker(dirname, dockerprefix, tag, basename, config, verbose = False, nocache = False ):
	infra_dockers = config["infrastructure-dockers"] if "infrastructure-dockers" in config else {}
	infra_docker_registry = config["infrastructure-dockerregistry"] if "infrastructure-dockerregistry" in config else config["dockerregistry"]
	worker_docker_registry = config["worker-dockerregistry"] if "worker-dockerregistry" in config else config["dockerregistry"]
	dockername = build_one_docker( dirname, dockerprefix, tag, basename, verbose = verbose, nocache = nocache )
	if basename in infra_dockers:
		push_docker( dockername, infra_docker_registry, verbose )
	else:
		push_docker( dockername, worker_docker_registry, verbose )	
	return dockername
				
def push_dockers(rootdir, dockerprefix, dockertag, nargs, config, verbose = False, nocache = False ):
	infra_dockers = config["infrastructure-dockers"] if "infrastructure-dockers" in config else {}
	infra_docker_registry = config["infrastructure-dockerregistry"] if "infrastructure-dockerregistry" in config else config["dockerregistry"]
	worker_docker_registry = config["worker-dockerregistry"] if "worker-dockerregistry" in config else config["dockerregistry"]
	docker_list = get_docker_list(rootdir, dockerprefix, dockertag, nargs, verbose ); 
	for dockername, tuple in docker_list.iteritems():
		build_docker(dockername, tuple[1], verbose, nocache = nocache )
		if tuple[0] in infra_dockers:
			if verbose: 
				print "Push to infrastructure docker register %s with name %s" % ( infra_docker_registry , dockername )
			push_docker(dockername, infra_docker_registry, verbose)
		else:
			if verbose: 
				print "Push to worker docker register %s with name %s" % ( worker_docker_registry , dockername )	
			push_docker(dockername, worker_docker_registry, verbose)

def copy_from_docker_image(image, srcFile, dstFile):
	id = subprocess.check_output(['docker', 'create', image])
	id = id.strip()
	copyCmd = "docker cp --follow-link=true " + id + ":" + srcFile + " " + dstFile
	#print copyCmd
	os.system(copyCmd)
	os.system("docker rm -v " + id)
