# Setup Kubernetes Development Environment. 

This document describes the procedure to setup the Kubernetes development environment that is needed for DL cluster deployment in docs/deployment. 

Currently, DL workspace requires a multi-gpu aware Kubernetes build. Please access the Kubernetes build from either:

  `https://github.com/jinlmsft/kubernetes [branch multigpu-investigate1]`
or `https://github.com/sanjeevm0/kubernetes [branch multigpu-investigate]`

We will need to build a local binary, output at _output/bin. As such, we need to install golang. Kubernetes needs Go version 1.6 and up, which the apt-get utility for Ubuntu 12.04 and 14.04 will only install Go version 1.4. As such, we will need the following procedures (please see explanation on http://www.hostingadvice.com/how-to/install-golang-on-ubuntu/) to install a moore latest Version of Go  (1.7.4). 

1. Clone GVM Repo and Add to user directory.

  `bash < <(curl -s -S -L https://raw.githubusercontent.com/moovweb/gvm/master/binscripts/gvm-installer)`

2. Open ~/.bashrc and Source the GVM directory. 

  `[[ -s "$HOME/.gvm/scripts/gvm" ]] && source "$HOME/.gvm/scripts/gvm"`

3. Logout and relogin. 

  The changes in .bashrc will take effect.

4. Check version of Go that are available.  

  `gvm listall`

5. Install Go Version 1.4.

  `gvm install go1.4`

6. Use Go Version 1.4 as the bootstrap for more advanced Go version installation. 
Please note direct installation of a higher version of Go will fail without Go Version 1.4 to bootstrap. 

  `gvm use go1.4`
  `export GOROOT_BOOTSTRAP=$GOROOT`

7. You may now install and use more advanced Go version. 

  `gvm install go1.7.4`
  `gvm use go1.7.4`

8. After a proper Go version installed (Go 1.6+), you may build the needed Kubernetes binary by:

  `make`

at Kubernetes home directory. The needed output is at `_output/bin`. 
