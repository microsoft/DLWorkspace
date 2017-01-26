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

# prefix and tag will be filled by argument parser.
dockerprefix = ""
dockertag = ""
dirname = "devenv"

class cd:
    """Context manager for changing the current working directory"""
    def __init__(self, newPath):
        self.newPath = os.path.expanduser(newPath)

    def __enter__(self):
        self.savedPath = os.getcwd()
        os.chdir(self.newPath)

    def __exit__(self, etype, value, traceback):
        os.chdir(self.savedPath)

def buildDocker():
	dockername = dockerprefix+":"+dockertag
	print "Building docker ... " + dockername
	with cd(dirname):
		os.system("docker build -t "+ dockername + " .")
	return dockername
	
def runDocker(dockername):
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
	fw.write("export HOME="+homedir+"\n")
	fw.write("cd "+currentdir+"\n")
	fw.write("dockerd > /dev/null 2>&1 &\n")
	fw.write("su -m "+username +"\n")
	fw.close()
	os.chmod(wname, 0755)
	if homedir in currentdir:
		cmd = "docker run --privileged --hostname DevDocker --rm -ti -v " + homedir + ":"+homedir + " -v "+dirname+ ":/tmp/runcommand -w "+homedir + " " + dockername + " /tmp/runcommand/run.sh"
	else:
		cmd = "docker run --privileged --hostname DevDocker --rm -ti -v " + homedir + ":"+homedir + " -v "+ currentdir + ":" + currentdir + " -v "+dirname+ ":/tmp/runcommand -w "+homedir + " " + dockername + " /tmp/runcommand/run.sh"
	print "Execute: " + cmd
	os.system(cmd)
	
	
if __name__ == '__main__':
	parser = argparse.ArgumentParser(description = "Run a docker for development of DL workspace")
	parser.add_argument("-p", "--prefix", 
		help="Prefix of the docker name, or [dev]", 
		action="store", 
		default="dev" )
	parser.add_argument("-t", "--tag", 
		help="Tag of the docker build, or [current]", 
		action = "store", 
		default = "current" )
	args = parser.parse_args()
	dockerprefix = args.prefix
	dockertag = args.tag
	
	dockername = buildDocker()
	runDocker(dockername)
