# Development docker of DLWorkspace

* Prerequisite: python and docker. 
  If your system is Ubuntu, and hasn't installed python and docker, please run the following to install the required development environment for DL Workspace. If you are using other flavor of Linux or using other system, please consult its instruction on installing docker, python, and other required component. 
  ```
  ./install_prerequisites.sh 
  ```
  
* Run inside Development docker. 
  ```
  python devenv.py
  ```
  Once successfully executed, you will run inside a development docker, which contains all the necessary tools for DLWorkspace development. Your home folder & current directory is mapped in the development docker. You have sudo priviledge inside the development docker. You may notice that you are running in a development docker by prompt:
  
  username@**__DevDocker__**:directory$

