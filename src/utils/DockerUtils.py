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

def buildDocker( dockername, dirname):
	# docker name is designed to use lower case. 
	dockername = dockername.lower()
	print "Building docker ... " + dockername + " .. @" + dirname
	with cd(dirname):
		cmd = "docker build -t "+ dockername + " ."
		os.system(cmd)
	return dockername
	
def runDocker(dockername, prompt=""):
	currentdir = os.path.abspath(os.getcwd())
	uid = os.getuid()
	username = getpass.getuser()
	username = username.split()[0]
	groupid = pwd.getpwnam(username).pw_gid
	groupname = grp.getgrgid(groupid).gr_name
	groupname = groupname.split()[0]
	homedir = expanduser("~")
	print "Running docker " + dockername + " as Userid: " + str(uid) + "(" + username +"), + Group:"+str(groupid) + "("+groupname+") at " + homedir
	dirname = tempfile.mkdtemp()
	wname = os.path.join(dirname,"run.sh")
	fw = open( wname, "w+" )
	fw.write("#!/bin/bash\n")
	fw.write("addgroup --force-badname --gid "+str(groupid)+" " +groupname+"\n")
	fw.write("adduser --force-badname --home " + homedir + " --shell /bin/bash --no-create-home --uid " + str(uid)+ " -gecos '' "+username+" --disabled-password --gid "+str(groupid)+"\n" )
	fw.write("adduser "+username +" sudo\n")
	fw.write("adduser "+username +" docker\n")
	fw.write("echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers\n")
	fw.write("chmod --recursive 0755 /root\n")
	# Please note: setting HOME environment in docker may nullify additional environment variables, 
	# such as GOPATH.
	fw.write("export HOME="+homedir+"\n")
	fw.write("cd "+currentdir+"\n")
	fw.write("dockerd > /dev/null 2>&1 &\n")
	fw.write("""echo "export PATH=\$PATH:\$GOPATH/bin" | cat >> /etc/bash.bashrc \n""")
	fw.write("""echo "export GOPATH=\$GOPATH" | cat >> /etc/bash.bashrc \n""")
	fw.write("su -m "+username +"\n")
	fw.close()
	os.chmod(wname, 0755)
	if prompt == "":
		hostname = "Docker["+dockername+"]"
	else:
		hostname = prompt
	if homedir in currentdir:
		cmd = "docker run --privileged --hostname " + hostname + " --rm -ti -v " + homedir + ":"+homedir + " -v "+dirname+ ":/tmp/runcommand -w "+homedir + " " + dockername + " /tmp/runcommand/run.sh"
	else:
		cmd = "docker run --privileged --hostname " + hostname + " --rm -ti -v " + homedir + ":"+homedir + " -v "+ currentdir + ":" + currentdir + " -v "+dirname+ ":/tmp/runcommand -w "+homedir + " " + dockername + " /tmp/runcommand/run.sh"
	print "Execute: " + cmd
	os.system(cmd)
	
def findDockers( dockername):
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
	matchdockers = []
	for i in range(2,numlines):
		imageinfo = lines[i].split()
		imagename = imageinfo[0]+":"+imageinfo[1]
		if dockername in imagename:
			matchdockers.append(imagename)
	return matchdockers

def buildAllDockers(rootdir, dockerprefix, dockertag, nargs, verbose = False ):
	if not (nargs is None) and len(nargs)>0:
		nargs = map(lambda x:x.lower(), nargs )
	fnames = os.listdir(rootdir)
	for fname in fnames:
		if nargs is None or len(nargs)==0 or fname.lower() in nargs:
			entry = os.path.join(rootdir, fname )
			if os.path.isdir(entry):
				dockername = dockerprefix + os.path.basename(entry)+":"+dockertag
				buildDocker(dockername, entry)
