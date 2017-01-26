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

class cd:
    """Context manager for changing the current working directory"""
    def __init__(self, newPath):
        self.newPath = os.path.expanduser(newPath)

    def __enter__(self):
        self.savedPath = os.getcwd()
        os.chdir(self.newPath)

    def __exit__(self, etype, value, traceback):
        os.chdir(self.savedPath)

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
	
def runDocker(dockername):
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
	fw.write("echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers\n")
	fw.write("chmod --recursive 0755 /root\n")
	fw.write("su -m "+username +" -c /bin/bash\n")
	fw.close()
	os.chmod(wname, 0755)
	cmd = "docker run --rm -ti -v " + homedir + ":"+homedir + " -v "+dirname+ ":/tmp/runcommand -w "+homedir + " " + dockername + " /tmp/runcommand/run.sh"
	
	
	print "Execute: " + cmd
	os.system(cmd)
	
	
if __name__ == '__main__':
	parser = argparse.ArgumentParser(description = "Run a docker using your own credential")
	parser.add_argument("dockername", 
		help="docker to be run",
		action="store",
		type=str, 
		nargs=1)
	args = parser.parse_args()
	dockers = args.dockername
	if len(dockers)>1:
		parser.print_help()
		print "Please specify only one dockername to run ... "+ dockers
	else:
		for docker in dockers:
			matchdockers = findDockers(docker)
			if len(matchdockers)>1:
				parser.print_help()
				print "Multiple docker images match the current name"
				for dockername in matchdockers:
					print "Docker images ....    " + dockername
				print "Please specify a specific docker to run"
				exit()
			else:
				for dockername in matchdockers:
					runDocker(dockername)
