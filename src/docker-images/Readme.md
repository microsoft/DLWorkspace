# Docker images used in DL workspace. 

* clusterportal: docker for cluster portal
* deploy: docker for (deploying DL workspace)[../../docs/deployment/Readme.md]

Please use './deploy.py docker build' to build all docker images used in the project. 

You may use './deploy.py docker run' to execuate a particular docker image with your own user credential. By default, user run with 'root' in docker, and all files generated are authored by root. 'run.py' attempt to map your userid inside docker, and run the docker with your userid, if the OS of your docker image support such credential change. 

* Additional Command

If file exist, command prebuild.sh will be executed before the docker build. 



