import argparse
import sys
sys.path.append("../utils")
sys.path.append("../../../utils")
from DockerUtils import buildDocker, runDocker, findDockers

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
					runDocker(dockername )
