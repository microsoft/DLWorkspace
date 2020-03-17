#!/usr/bin/env python3

import os
import sys
import subprocess
import tempfile
import getpass
import pwd
import grp
from os.path import expanduser
from DirectoryUtils import cd


def build_docker(dockername, dirname, verbose=False, nocache=False):
    # docker name is designed to use lower case.
    dockername = dockername.lower()
    if verbose:
        print("Building docker ... " + dockername + " .. @" + dirname)

    try:
        output = subprocess.check_output(["git", "rev-parse", "HEAD"])
        git_hash = output.decode("utf-8").strip()
    except Exception:
        git_hash = "unknown"

    with cd(dirname):
        # print "Test if prebuid.sh exists"
        if os.path.exists("prebuild.sh"):
            print("Execute prebuild.sh for docker %s" % dockername)
            os.system("bash prebuild.sh")

        build_args = "--build-arg GIT_HASH=%s" % (git_hash)

        if nocache:
            build_args += " --no-cache"

        cmd = "docker build %s -t %s ." % (build_args, dockername)

        if verbose:
            print(cmd)
        os.system(cmd)
    return dockername


def build_docker_with_config(dockername, config, verbose=False, nocache=False):
    usedockername = dockername.lower()
    build_docker(config["dockers"]["container"][dockername]["name"],
                 config["dockers"]["container"][dockername]["dirname"], verbose,
                 nocache)


def push_docker(dockername, docker_register, verbose=False):
    # docker name is designed to use lower case.
    dockername = dockername.lower()
    if verbose:
        print("Pushing docker ... " + dockername + " to " + docker_register)
    cmd = "docker tag " + dockername + " " + docker_register + dockername
    cmd += "; docker push " + docker_register + dockername
    os.system(cmd)
    return dockername


def push_docker_with_config(dockername, config, verbose=False, nocache=False):
    usedockername = dockername.lower()
    # build_docker( config["dockers"]["container"][dockername]["name"], config["dockers"]["container"][dockername]["dirname"], verbose, nocache )
    if verbose:
        print("Pushing docker ... " +
              config["dockers"]["container"][dockername]["name"] + " to " +
              config["dockers"]["container"][dockername]["fullname"])
    cmd = "docker tag " + config["dockers"]["container"][dockername][
        "name"] + " " + config["dockers"]["container"][dockername]["fullname"]
    cmd += "; docker push " + config["dockers"]["container"][dockername][
        "fullname"]
    if verbose:
        print(cmd)
    os.system(cmd)
    return config["dockers"]["container"][dockername]["name"]


def run_docker(dockername,
               prompt="",
               dockerConfig=None,
               sudo=False,
               options=""):
    if not (dockerConfig is None):
        if "su" in dockerConfig:
            sudo = True
        if "options" in dockerConfig and len(options) <= 0:
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
            for volume, mapping in dockerConfig["volumes"].items():
                if "from" in mapping and "to" in mapping:
                    mapdir = os.path.abspath(mapping["from"])
                    mapVolume += " -v " + mapdir + ":" + mapping["to"]
    else:
        if not (homedir in currentdir):
            mapVolume += " -v " + currentdir + ":" + currentdir
    mapVolume += " --net=host"
    print("Running docker " + dockername + " as Userid: " + str(uid) + "(" +
          username + "), + Group:" + str(groupid) + "(" + groupname + ") at " +
          homedir)
    dirname = tempfile.mkdtemp()
    wname = os.path.join(dirname, "run.sh")
    fw = open(wname, "w+")
    fw.write("#!/bin/bash\n")
    fw.write("if [ -f /etc/lsb-release ]; then \n")
    fw.write("addgroup --force-badname --gid " + str(groupid) + " " +
             groupname + "\n")
    fw.write("adduser --force-badname --home " + homedir +
             " --shell /bin/bash --no-create-home --uid " + str(uid) +
             " -gecos '' " + username + " --disabled-password --gid " +
             str(groupid) + "\n")
    fw.write("adduser " + username + " sudo\n")
    fw.write("adduser " + username + " docker\n")
    fw.write("fi\n")
    fw.write("if [ -f /etc/redhat-release ]; then \n")
    fw.write("groupadd --gid " + str(groupid) + " " + groupname + "\n")
    fw.write("useradd  --home " + homedir +
             " --shell /bin/bash --no-create-home --uid " + str(uid) + " " +
             username + " --password '' --gid " + str(groupid) + "\n")
    fw.write("usermod -aG wheel " + username + "\n")
    fw.write("fi\n")
    fw.write("echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers\n")
    fw.write("chmod --recursive 0755 /root\n")
    # Please note: setting HOME environment in docker may nullify additional environment variables,
    # such as GOPATH.
    fw.write("export HOME=" + homedir + "\n")
    fw.write("cd " + currentdir + "\n")
    fw.write("dockerd > /dev/null 2>&1 &\n")
    fw.write(
        """echo "export PATH=\$PATH:\$GOPATH/bin" | cat >> /etc/bash.bashrc \n"""
    )
    fw.write("""echo "export GOPATH=\$GOPATH" | cat >> /etc/bash.bashrc \n""")
    if not sudo:
        fw.write("su -m " + username + "\n")
    else:
        print("Run in super user mode...")
        fw.write("/bin/bash")
    fw.close()
    os.chmod(wname, 0o755)
    if prompt == "":
        hostname = "Docker[" + dockername + "]"
    else:
        hostname = prompt
    if homedir in currentdir:
        cmd = "docker run --privileged --hostname " + hostname + " " + options + " --rm -ti " + mapVolume + " -v " + dirname + ":/tmp/runcommand -w " + homedir + " " + dockername + " /tmp/runcommand/run.sh"
    else:
        cmd = "docker run --privileged --hostname " + hostname + " " + options + " --rm -ti " + mapVolume + " -v " + dirname + ":/tmp/runcommand -w " + homedir + " " + dockername + " /tmp/runcommand/run.sh"
    print("Execute: " + cmd)
    os.system(cmd)


def find_dockers(dockername):
    print("Search for dockers .... " + dockername)
    tmpf = tempfile.NamedTemporaryFile()
    tmpfname = tmpf.name
    tmpf.close()
    #os.remove(tmpfname)
    dockerimages_all = os.system("docker images > " + tmpfname)
    with open(tmpfname, "r") as dockerimage_file:
        lines = dockerimage_file.readlines()
    os.remove(tmpfname)
    numlines = len(lines)
    dockerdics = {}
    for i in range(1, numlines):
        imageinfo = lines[i].split()
        if imageinfo == "<none>":
            imagename = imageinfo[0]
        else:
            imagename = imageinfo[0] + ":" + imageinfo[1]
        if dockername in imagename:
            dockerdics[imagename] = True
    matchdockers = list(dockerdics.keys())
    return matchdockers


def build_docker_fullname(config, dockername, verbose=False):
    dockername = dockername.lower()
    if dockername in config["dockers"]["container"]:
        return config["dockers"]["container"][dockername]["fullname"], config[
            "dockers"]["container"][dockername]["name"]
    dockerprefix = config["dockerprefix"]
    dockertag = config["dockertag"]
    infra_dockers = config[
        "infrastructure-dockers"] if "infrastructure-dockers" in config else {}
    infra_docker_registry = config[
        "infrastructure-dockerregistry"] if "infrastructure-dockerregistry" in config else config[
            "dockerregistry"]
    worker_docker_registry = config[
        "worker-dockerregistry"] if "worker-dockerregistry" in config else config[
            "dockerregistry"]
    if dockername in infra_dockers:
        return (infra_docker_registry + dockerprefix + dockername + ":" +
                dockertag).lower(), (dockerprefix + dockername + ":" +
                                     dockertag).lower()
    else:
        return (worker_docker_registry + dockerprefix + dockername + ":" +
                dockertag).lower(), (dockerprefix + dockername + ":" +
                                     dockertag).lower()


def get_docker_list(rootdir, dockerprefix, dockertag, nargs, verbose=False):
    docker_list = {}
    if not (nargs is None) and len(nargs) > 0:
        nargs = [x.lower() for x in nargs]
    fnames = os.listdir(rootdir)
    for fname in fnames:
        if nargs is None or len(nargs) == 0 or fname.lower() in nargs:
            entry = os.path.join(rootdir, fname)
            if os.path.isdir(entry):
                basename = os.path.basename(entry)
                dockername = dockerprefix + os.path.basename(
                    entry) + ":" + dockertag
                docker_list[dockername] = (basename, entry)
    return docker_list


system_docker_registry = None


def config_dockers_use_tag(rootdir, config, verbose):
    global system_docker_registry
    if system_docker_registry is None:
        docker_registry = config["dockers"]["hub"]
        system_docker_registry = docker_registry
        docker_prefix = config["dockers"]["prefix"]
        docker_tag = config["dockers"]["tag"]
        docker_list = get_docker_list(rootdir, "", "", None, verbose)
        # Populate system dockers
        for assemblename, tupl in docker_list.items():
            # print assemblename
            dockername, deploydir = tupl
            usedockername = docker_registry + "/" + docker_prefix + ":" + dockername + "-" + docker_tag
            usedockername = usedockername.lower()
            if "container" not in config["dockers"]:
                config["dockers"]["container"] = {}
            config["dockers"]["container"][dockername] = {
                "dirname": os.path.join("./deploy/docker-images", dockername),
                "fullname": usedockername,
                "name": usedockername,
            }


def configuration(config, verbose):
    config_dockers("../docker-images", config["dockerprefix"],
                   config["dockertag"], verbose, config)


def config_dockers(rootdir, dockerprefix, dockertag, verbose, config):
    global system_docker_registry
    global system_docker_tag
    global system_docker_dic
    global infra_docker_registry
    global worker_docker_registry
    if system_docker_registry is None:
        infra_dockers = config["infrastructure-dockers"] if "infrastructure-dockers" in config else {}
        infra_docker_registry = config[
            "infrastructure-dockerregistry"] if "infrastructure-dockerregistry" in config else config[
                "dockerregistry"]
        worker_docker_registry = config[
            "worker-dockerregistry"] if "worker-dockerregistry" in config else config[
                "dockerregistry"]
        system_docker_registry = config["dockers"]["hub"]
        system_docker_tag = config["dockers"]["tag"]
        system_docker_dic = config["dockers"]["system"]
        docker_list = get_docker_list(rootdir, dockerprefix, dockertag, None,
                                      verbose)
        # Populate system dockers
        for assemblename, tupl in list(docker_list.items()):
            # print assemblename
            dockername, deploydir = tupl
            if dockername in system_docker_dic:
                # system docker
                tag = system_docker_dic[dockername][
                    "tag"] if "tag" in system_docker_dic[
                        dockername] else system_docker_tag
                prefix = ""
                # dirname = os.path.join(rootdir, dockername)
                # our target is to use rootdir/dockername in the future
                dirname = deploydir
                dockerregistry = system_docker_registry
            else:
                tag = dockertag
                prefix = dockerprefix
                dirname = deploydir
                if dockername in infra_dockers:
                    dockerregistry = infra_docker_registry
                else:
                    dockerregistry = worker_docker_registry
            # overwrite dockerregistry if want to use other registry
            if "private_docker_registry" in config:
                dockerregistry = config["private_docker_registry"].get(
                    dockername, dockerregistry)
            usedockername = dockername.lower()
            if "container" not in config["dockers"]:
                config["dockers"]["container"] = {}
            config["dockers"]["container"][dockername] = {
                "dirname":
                    os.path.join("./deploy/docker-images", dockername),
                "fullname":
                    '/'.join([dockerregistry, prefix, usedockername]) + ":" +
                    tag,
                "name":
                    '/'.join([prefix, usedockername]) + ":" + tag,
            }
        # pxe-ubuntu and pxe-coreos is in template
        for dockername in config["dockers"]["infrastructure"]:
            config["dockers"]["container"][dockername] = {
                "dirname":
                    os.path.join("./deploy/docker-images", dockername),
                "fullname":
                    '/'.join([infra_docker_registry, dockerprefix, dockername])
                    + ":" + dockertag,
                "name":
                    '/'.join([dockerprefix, dockername]) + ":" + dockertag,
            }
        # pxe-ubuntu and pxe-coreos is in template
        for dockername in config["dockers"]["external"]:
            usedockername = dockername.lower()
            config["dockers"]["container"][dockername] = {}
            if "fullname" in config["dockers"]["external"][dockername]:
                config["dockers"]["container"][dockername]["fullname"] = config[
                    "dockers"]["external"][dockername]["fullname"]
            else:
                config["dockers"]["container"][dockername][
                    "fullname"] = system_docker_registry + usedockername + ":" + system_docker_tag

            if "name" in config["dockers"]["external"][dockername]:
                config["dockers"]["container"][dockername]["name"] = config[
                    "dockers"]["external"][dockername]["name"]
            else:
                config["dockers"]["container"][dockername][
                    "name"] = usedockername + ":" + system_docker_tag

        # print config["dockers"]


def build_dockers(rootdir,
                  dockerprefix,
                  dockertag,
                  nargs,
                  config,
                  verbose=False,
                  nocache=False):
    configuration(config, verbose)
    docker_list = get_docker_list(rootdir, dockerprefix, dockertag, nargs,
                                  verbose)
    # print rootdir
    for _, tupl in docker_list.items():
        dockername, _ = tupl
        build_docker_with_config(dockername, config, verbose, nocache=nocache)


def build_one_docker(dirname,
                     dockerprefix,
                     dockertag,
                     basename,
                     config,
                     verbose=False,
                     nocache=False):
    configuration(config, verbose)
    return build_docker_with_config(basename, config, verbose, nocache=nocache)


def push_one_docker(dirname,
                    dockerprefix,
                    tag,
                    basename,
                    config,
                    verbose=False,
                    nocache=False):
    configuration(config, verbose)
    build_docker_with_config(basename, config, verbose, nocache=nocache)
    push_docker_with_config(basename, config, verbose, nocache=nocache)


def push_dockers(rootdir,
                 dockerprefix,
                 dockertag,
                 nargs,
                 config,
                 verbose=False,
                 nocache=False):
    configuration(config, verbose)
    docker_list = get_docker_list(rootdir, dockerprefix, dockertag, nargs,
                                  verbose)
    for _, tupl in docker_list.items():
        dockername, _ = tupl
        build_docker_with_config(dockername, config, verbose, nocache=nocache)
        push_docker_with_config(dockername, config, verbose, nocache=nocache)


def copy_from_docker_image(image, srcFile, dstFile):
    pid = subprocess.check_output(['docker', 'create', image])
    pid = pid.strip()
    if sys.version_info >= (3, 0):
        pid = str(pid, 'utf-8')
    copyCmd = "docker cp --follow-link=true " + pid + ":" + srcFile + " " + dstFile
    os.system(copyCmd)
    os.system("docker rm -v " + pid)
