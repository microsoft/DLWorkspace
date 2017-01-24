# Docker images used in DL workspace. 

* clusterportal: docker for cluster portal
* deploy: docker for (deploying DL workspace)[../../docs/deployment/README.md]

Please use 'build.py' to build all docker images used in the project. 

Please use 'run.py' to execuate a particular docker image with your own user credential. By default, user run with 'root' in docker, and all files generated are authored by root. 'run.py' attempt to map your userid inside docker, and run the docker with your userid. 

