#!/usr/bin/env python3

import socket
import json
import os
import time
import datetime
import argparse
import uuid
import subprocess
from multiprocessing import Pool
import sys
import textwrap
import re
import math
import distutils.dir_util
import distutils.file_util
import shutil
import glob
import random
import string
import requests
import urllib.parse

import yaml
from jinja2 import Environment, FileSystemLoader, Template
import base64

from shutil import copyfile, copytree
import urllib
import socket
import struct

verbose = False


class StaticVariable():
    rendered_target_directory = {}


def tolist(val):
    if isinstance(val, list):
        return val
    else:
        return [val]


def clean_rendered_target_directory():
    StaticVariable.rendered_target_directory = {}


def render_template(template_file, target_file, config, verbose=False):
    filename, file_extension = os.path.splitext(template_file)
    basename = os.path.basename(template_file)
    if ("render-exclude" in config and basename in config["render-exclude"]):
        # Don't render/copy the file.
        return
    if ("render-by-copy-ext" in config and
            file_extension in config["render-by-copy-ext"]) or (
                "render-by-copy" in config and
                basename in config["render-by-copy"]):
        copyfile(template_file, target_file)
        if verbose:
            print("Copy tempalte " + template_file + " --> " + target_file)
    elif "render-by-copy-full" in config and template_file in config[
            "render-by-copy-full"]:
        copyfile(template_file, target_file)
        if verbose:
            print("Copy tempalte " + template_file + " --> " + target_file)
    elif ("render-by-line-ext" in config and
          file_extension in config["render-by-line-ext"]) or (
              "render-by-line" in config and
              basename in config["render-by-line"]):
        if verbose:
            print("Render template " + template_file + " --> " + target_file +
                  " Line by Line .... ")
        ENV_local = Environment(loader=FileSystemLoader("/"))
        with open(target_file, 'w') as f:
            with open(template_file, 'r') as fr:
                for line in fr:
                    print("Read: " + line)
                    try:
                        template = ENV_local.Template(line)
                        content = template.render(cnf=config)
                        print(content)
                        f.write(content + "\n")
                    except:
                        pass
                fr.close()
            f.close()

    else:
        if verbose:
            print("Render template " + template_file + " --> " + target_file)
        try:
            ENV_local = Environment(loader=FileSystemLoader("/"))
            template = ENV_local.get_template(os.path.abspath(template_file))
            content = template.render(cnf=config)
            target_dir = os.path.dirname(target_file)
            if target_dir != '':
                os.system("mkdir -p {0}".format(target_dir))
            with open(target_file, 'w') as f:
                f.write(content)
            f.close()
        except Exception as e:
            print("!!! Failure !!! in render template " + template_file)
            print(e)
            pass


def render_template_directory(template_dir,
                              target_dir,
                              config,
                              verbose=False,
                              exclude_dir=None):
    if target_dir in StaticVariable.rendered_target_directory:
        return
    else:
        StaticVariable.rendered_target_directory[target_dir] = template_dir
        os.system("mkdir -p " + target_dir)
        markfile = os.path.join(target_dir, "DO_NOT_WRITE")
        # print "Evaluate %s" % markfile
        if not os.path.exists(markfile):
            # print "Write DO_NOT_WRITE"
            open(markfile, 'w').close()
        if os.path.isfile(os.path.join(template_dir, "pre-render.sh")):
            pre_reder = os.path.join(template_dir, "pre-render.sh")
            os.system("sh " + pre_reder)
        filenames = os.listdir(template_dir)
        for filename in filenames:
            if filename == "copy_dir":
                fullname = os.path.join(template_dir, filename)
                with open(fullname) as f:
                    content = f.readlines()
                content = [x.strip() for x in content]
                for copy_dir in content:
                    fullname_copy_dir = os.path.join(template_dir, copy_dir)
                    # print "To render via copy %s" % fullname_copy_dir
                    # Allow target directory to be re-rendered
                    StaticVariable.rendered_target_directory.pop(
                        target_dir, None)
                    render_template_directory(fullname_copy_dir,
                                              target_dir,
                                              config,
                                              verbose,
                                              exclude_dir=template_dir)
            elif os.path.isfile(os.path.join(template_dir, filename)):
                if exclude_dir is not None:
                    check_file = os.path.join(exclude_dir, filename)
                    if os.path.exists(check_file):
                        continue
                render_template(os.path.join(template_dir, filename),
                                os.path.join(target_dir, filename), config,
                                verbose)
            else:
                srcdir = os.path.join(template_dir, filename)
                dstdir = os.path.join(target_dir, filename)
                if ("render-by-copy" in config and
                        filename in config["render-by-copy"]):
                    os.system("rm -rf %s" % dstdir)
                    os.system("cp -r %s %s" % (srcdir, dstdir))
                else:
                    if exclude_dir is None:
                        render_template_directory(srcdir, dstdir, config,
                                                  verbose)
                    else:
                        exdir = os.path.join(exclude_dir, filename)
                        render_template_directory(srcdir,
                                                  dstdir,
                                                  config,
                                                  verbose,
                                                  exclude_dir=exdir)
        if os.path.isfile(os.path.join(target_dir, "post-render.sh")):
            post_reder = os.path.join(target_dir, "post-render.sh")
            os.system("sh " + post_reder)


# Execute a remote SSH cmd with identity file (private SSH key), user, host


def SSH_exec_cmd(identity_file, user, host, cmd, showCmd=True):
    if len(cmd) == 0:
        return
    if showCmd or verbose:
        print(
            """ssh -q -o "StrictHostKeyChecking no" -o "UserKnownHostsFile=/dev/null" -i %s "%s@%s" "%s" """
            % (identity_file, user, host, cmd))
    os.system(
        """ssh -q -o "StrictHostKeyChecking no" -o "UserKnownHostsFile=/dev/null" -i %s "%s@%s" "%s" """
        % (identity_file, user, host, cmd))


# SSH Connect to a remote host with identity file (private SSH key), user, host
# Program usually exit here.


def SSH_connect(identity_file, user, host):
    if verbose:
        print(
            """ssh -q -o "StrictHostKeyChecking no" -o "UserKnownHostsFile=/dev/null" -i %s "%s@%s" """
            % (identity_file, user, host))
    os.system(
        """ssh -q -o "StrictHostKeyChecking no" -o "UserKnownHostsFile=/dev/null" -i %s "%s@%s" """
        % (identity_file, user, host))


# Copy a local file or directory (source) to remote (target) with identity file (private SSH key), user, host


def scp(identity_file, source, target, user, host, verbose=False):
    cmd = 'scp -q -o "StrictHostKeyChecking no" -o "UserKnownHostsFile=/dev/null" -i %s -r "%s" "%s@%s:%s"' % (
        identity_file, source, user, host, target)
    if verbose:
        print(cmd)
    os.system(cmd)


# Copy a local file (source) or directory to remote (target) with identity file (private SSH key), user, host, and


def sudo_scp(identity_file,
             source,
             target,
             user,
             host,
             changePermission=False,
             verbose=False):
    tmp = str(uuid.uuid4())
    scp(identity_file, source, "~/%s" % tmp, user, host, verbose)
    if (os.path.isfile(source)):
        target_path, target_base = os.path.split(target)
        target_base = os.path.basename(
            source) if target_base == '' else target_base
        target = os.path.join(target_path, target_base)
        cmd = "sudo mkdir -p %s ; sudo mv ~/%s %s" % (target_path, tmp, target)
    else:
        cmd = "sudo mkdir -p %s ; sudo rm -r %s/*; sudo mv ~/%s/* %s; sudo rm -rf ~/%s" % (
            target, target, tmp, target, tmp)
    if changePermission:
        cmd += " ; sudo chmod +x %s" % target
    # Force converting to dos format
    cmd += " ; sudo dos2unix %s" % target
    if verbose:
        print(cmd)
    SSH_exec_cmd(identity_file, user, host, cmd, verbose)


# Execute a remote SSH cmd with identity file (private SSH key), user, host
# Return the output of the remote command to local


def SSH_exec_cmd_with_output1(identity_file,
                              user,
                              host,
                              cmd,
                              supressWarning=False):
    tmpname = os.path.join("/tmp", str(uuid.uuid4()))
    execcmd = cmd + " > " + tmpname
    if supressWarning:
        execcmd += " 2>/dev/null"
    SSH_exec_cmd(identity_file, user, host, execcmd)
    scpcmd = 'scp -i %s "%s@%s:%s" "%s"' % (identity_file, user, host, tmpname,
                                            tmpname)
    # print scpcmd
    os.system(scpcmd)
    SSH_exec_cmd(identity_file, user, host, "rm " + tmpname)
    with open(tmpname, "r") as outputfile:
        output = outputfile.read()
    os.remove(tmpname)
    return output


def SSH_exec_cmd_with_output(identity_file,
                             user,
                             host,
                             cmd,
                             supressWarning=False):
    if len(cmd) == 0:
        return ""
    if supressWarning:
        cmd += " 2>/dev/null"
    execmd = """ssh -o "StrictHostKeyChecking no" -o "UserKnownHostsFile=/dev/null" -i %s "%s@%s" "%s" """ % (
        identity_file, user, host, cmd)
    if verbose:
        print(execmd)
    try:
        output = subprocess.check_output(execmd, shell=True)
    except subprocess.CalledProcessError as e:
        output = "Return code: " + \
            str(e.returncode) + ", output: " + e.output.strip()
    # print output
    return output


# This is an auxilary utility. It scan an IP range (e.g., 10.209.x.x/21, and find all notes that belong to the current cluster)


def SSH_exec_cmd_batchmode_with_output(identity_file, user, host, cmd):
    if len(cmd) == 0:
        return ""
    execmd = """timeout 3s ssh -oBatchMode=yes -o "StrictHostKeyChecking no" -o "UserKnownHostsFile=/dev/null" -i %s "%s@%s" "%s" 2>/dev/null """ % (
        identity_file, user, host, cmd)
    if verbose:
        print(execmd)
    try:
        output = subprocess.check_output(execmd, shell=True)
    except subprocess.CalledProcessError as e:
        output = "Return code: " + \
            str(e.returncode) + ", output: " + e.output.strip()
    # print output
    return output


def scan_nodes(identity_file, user, iprange):
    infos = iprange.split("/")
    if len(infos) != 2:
        print("IP range %s need to be formated as x.x.x.x/n" % iprange)
    else:
        ip = infos[0]
        size = 32 - int(infos[1])
        mask = (1 << size) - 1
        ipnum = struct.unpack("!L", socket.inet_aton(ip))[0]
        ipbase = ipnum & (~mask)
        for i in range(mask + 1):
            ipexamine = ipbase + i
            low8 = ipexamine & 0xff
            if low8 >= 2:
                host = socket.inet_ntoa(struct.pack('!L', ipexamine))
                sys.stdout.write(".")
                sys.stdout.flush()
                output = SSH_exec_cmd_batchmode_with_output(
                    identity_file, user, host, "echo hello")
                if output.find("hello") >= 0:
                    print("\n" + host)


def json_load_byteified(file_handle):
    return _byteify(json.load(file_handle, object_hook=_byteify),
                    ignore_dicts=True)


def json_loads_byteified(json_text):
    return _byteify(json.loads(json_text, object_hook=_byteify),
                    ignore_dicts=True)


# Get string objects instead of Unicode from JSON


def _byteify(data, ignore_dicts=False):
    # if this is a unicode string, return its string representation
    if isinstance(data, str):
        return data.encode('utf-8')
    # if this is a list of values, return list of byteified values
    if isinstance(data, list):
        return [_byteify(item, ignore_dicts=True) for item in data]
    # if this is a dictionary, return dictionary of byteified keys and values
    # but only if we haven't already byteified it
    if isinstance(data, dict) and not ignore_dicts:
        return {
            _byteify(key, ignore_dicts=True): _byteify(value, ignore_dicts=True)
            for key, value in data.items()
        }
    # if it's anything else, return it in its original form
    return data


def exec_cmd_local(execmd, verbose=False, max_run=1200, supressWarning=False):
    """subprocess.check_output is blocking function. for nonblocking option, resort to subprocess.Popen"""
    if supressWarning:
        execmd += " 2>/dev/null"
    if verbose:
        print(execmd)
    try:
        output = subprocess.check_output(execmd,
                                         timeout=max_run,
                                         shell=True,
                                         universal_newlines=True)
    except subprocess.CalledProcessError as e:
        output = "Return code: " + \
            str(e.returncode) + ", output: " + e.output.strip()
    if verbose:
        print(output)
    return output


def execute_or_dump_locally(cmd,
                            verbose,
                            dryrun,
                            output_file,
                            max_run=1200,
                            supress_warning=False):
    cmd = ' '.join(cmd.split())
    if output_file:
        with open(output_file, 'a') as wf:
            wf.write(cmd + '\n')
    if not dryrun:
        output = exec_cmd_local(cmd, verbose, max_run, supress_warning)
        return output


def multiprocess_with_func_arg_tuples(process_num, list_of_func_arg_tpls):
    pool = Pool(process_num)
    print("parallel pool of size {}".format(process_num))
    # returned would be in (return code, output err) format
    results = pool.map(multiprocess_func_wrapper, list_of_func_arg_tpls)
    pool.close()
    return results


def multiprocess_func_wrapper(func_arg_tpl):
    func, args = func_arg_tpl[0], func_arg_tpl[1:]
    result = func(*args)
    return result


def get_host_name(identity_file, user, host):
    execmd = """ssh -o "StrictHostKeyChecking no" -o "UserKnownHostsFile=/dev/null" -i %s "%s@%s" "hostname" """ % (
        identity_file, user, host)
    try:
        output = subprocess.check_output(execmd, shell=True)
    except subprocess.CalledProcessError as e:
        return "Exception, with output: " + e.output.strip()
    return output.strip()


def get_mac_address(identity_file, user, host, show=True):
    output = SSH_exec_cmd_with_output(identity_file, user, host, "ifconfig")
    etherMatch = re.compile(
        "ether [0-9a-f][0-9a-f]:[0-9a-f][0-9a-f]:[0-9a-f][0-9a-f]:[0-9a-f][0-9a-f]:[0-9a-f][0-9a-f]:[0-9a-f][0-9a-f]"
    )
    iterator = etherMatch.finditer(output)
    if show:
        print("Node " + host + " Mac address...")
        for match in iterator:
            print(match.group())
    macs = []
    for match in iterator:
        macs.append(match.group()[6:])
    return macs


# Execute a remote SSH cmd with identity file (private SSH key), user, host,
# Copy all directory of srcdir into a temporary folder, execute the command,
# and then remove the temporary folder.
# Command should assume that it starts srcdir, and execute a shell script in there.
# If dstdir is given, the remote command will be executed at dstdir, and its content won't be removed


def SSH_exec_cmd_with_directory(identity_file,
                                user,
                                host,
                                srcdir,
                                cmd,
                                supressWarning=False,
                                preRemove=True,
                                removeAfterExecution=True,
                                dstdir=None):
    if dstdir is None:
        tmpdir = os.path.join("/tmp", str(uuid.uuid4()))
        preRemove = False
    else:
        tmpdir = dstdir
        removeAfterExecution = False

    if preRemove:
        SSH_exec_cmd(identity_file, user, host, "sudo rm -rf " + tmpdir)
    scp(identity_file, srcdir, tmpdir, user, host, not supressWarning)
    dstcmd = "cd " + tmpdir + "; "
    if supressWarning:
        dstcmd += cmd + " 2>/dev/null; "
    else:
        dstcmd += cmd + "; "
    dstcmd += "cd /tmp; "
    if removeAfterExecution:
        dstcmd += "rm -r " + tmpdir + "; "
    SSH_exec_cmd(identity_file, user, host, dstcmd)


# Execute a remote SSH cmd with identity file (private SSH key), user, host,
# Copy a bash script a temporary folder, execute the script,
# and then remove the temporary file.
def SSH_exec_script(identity_file,
                    user,
                    host,
                    script,
                    supressWarning=False,
                    removeAfterExecution=True):
    tmpfile = os.path.join("/tmp", str(uuid.uuid4()) + ".sh")
    scp(identity_file, script, tmpfile, user, host)
    cmd = "bash --verbose " + tmpfile
    dstcmd = ""
    if supressWarning:
        dstcmd += cmd + " 2>/dev/null; "
    else:
        dstcmd += cmd + "; "
    if removeAfterExecution:
        dstcmd += "rm -r " + tmpfile + "; "
    SSH_exec_cmd(identity_file, user, host, dstcmd, False)


def get_ETCD_discovery_URL(size):
    if size == 1:
        output = "we don't use discovery url for 1 node etcd"
    else:
        try:
            output = urllib.urlopen("https://discovery.etcd.io/new?size=%d" %
                                    size).read()
            if not "https://discovery.etcd.io" in output:
                raise Exception(
                    "ERROR: we cannot get etcd discovery url from 'https://discovery.etcd.io/new?size=%d', got message %s"
                    % (size, output))
        except Exception as e:
            raise Exception(
                "ERROR: we cannot get etcd discovery url from 'https://discovery.etcd.io/new?size=%d'"
                % size)
    return output


def get_cluster_ID_from_file():
    clusterID = None
    if os.path.exists("./deploy/clusterID.yml"):
        f = open("./deploy/clusterID.yml")
        tmp = yaml.safe_load(f)
        f.close()
        if "clusterId" in tmp:
            clusterID = tmp["clusterId"]
    return clusterID


def gen_SSH_key(regenerate_key):
    print("===============================================")
    print("generating ssh key...")
    if regenerate_key:
        os.system("rm -rf ./deploy/sshkey")

    os.system("mkdir -p ./deploy/sshkey")
    if not os.path.exists("./deploy/sshkey/id_rsa"):
        os.system("ssh-keygen -t rsa -b 4096 -f ./deploy/sshkey/id_rsa -P ''")

    os.system("rm -rf ./deploy/kubelet")
    os.system("mkdir -p ./deploy/kubelet")


def setup_backup_dir(pname):
    deploy_backup_dir = os.path.abspath("./deploy_backup")
    backup_dir = os.path.join(deploy_backup_dir, "backup")
    pname = os.path.abspath(pname)

    pname_par = os.path.abspath(os.path.join(pname, os.pardir))
    backup_dir_par = os.path.abspath(os.path.join(backup_dir, os.pardir))

    assert pname_par != backup_dir_par

    if os.path.islink(backup_dir):
        os.system("rm %s" % backup_dir)
    else:
        os.system("rm -rf %s" % backup_dir)

    os.system("mkdir -p %s" % deploy_backup_dir)
    os.system("ln -s %s %s" % (pname, backup_dir))

    return backup_dir


def execute_backup_and_encrypt(clusterName, fname, key):
    clusterID = get_cluster_ID_from_file()
    backupdir = "./deploy_backup/backup"
    os.system("mkdir -p %s/clusterID" % backupdir)
    os.system("cp -r ./*.yaml %s" % backupdir)
    os.system("cp -r ./deploy/sshkey %s/sshkey" % backupdir)
    os.system("cp -r ./deploy/ssl %s/ssl" % backupdir)
    os.system("cp -r ./deploy/clusterID.yml %s/clusterID/" % backupdir)
    if os.path.exists("./deploy/acs_kubeclusterconfig"):
        os.system("cp -r ./deploy/acs_kubeclusterconfig %s/" % backupdir)
    os.system("tar -czvf %s.tar.gz %s" % (fname, backupdir))
    if not key is None:
        os.system(
            "openssl enc -aes-256-cbc -k %s -in %s.tar.gz -out %s.tar.gz.enc" %
            (key, fname, fname))
        os.system("rm %s.tar.gz" % fname)
    os.system("rm -rf ./deploy_backup/backup")


def execute_backup_to_dir(pname):
    os.system("mkdir -p %s" % pname)

    backup_dir = setup_backup_dir(pname)

    os.system("mkdir -p %s/clusterID" % backup_dir)
    os.system("cp -r ./*.yaml %s" % backup_dir)
    os.system("cp -r ./deploy/sshkey %s" % backup_dir)
    os.system("cp -r ./deploy/ssl %s" % backup_dir)
    os.system("cp -r ./deploy/*.yml %s/clusterID/" % backup_dir)
    if os.path.exists("./deploy/acs_kubeclusterconfig"):
        os.system("cp -r ./deploy/acs_kubeclusterconfig %s/" % backup_dir)


def execute_restore_and_decrypt(fname, key):
    clusterID = get_cluster_ID_from_file()
    backupdir = "./deploy_backup/backup"
    os.system("mkdir -p %s" % backupdir)
    cleanup_command = ""
    if fname.endswith(".enc"):
        if key is None:
            print("%s needs decrpytion key" % fname)
            exit(-1)
        fname = fname[:-4]
        os.system("openssl enc -d -aes-256-cbc -k %s -in %s.enc -out %s" %
                  (key, fname, fname))
        cleanup_command = "rm %s; " % fname
    os.system("tar -xzvf %s %s" % (fname, backupdir))
    os.system("cp -v %s/*.yaml ." % (backupdir))
    os.system("mkdir -p ./deploy/sshkey")
    os.system("mkdir -p ./deploy/ssl")
    os.system("cp -r %s/sshkey/* ./deploy/sshkey" % backupdir)
    if os.path.exists("%s/ssl/kubelet" % backupdir):
        os.system("cp -r %s/ssl/* ./deploy/ssl" % backupdir)
    os.system("cp %s/clusterID/*.yml ./deploy/" % backupdir)
    if os.path.exists("%s/acs_kubeclusterconfig" % backupdir):
        os.system("cp -r %s/acs_kubeclusterconfig ./deploy/" % backupdir)
    cleanup_command += "rm -rf ./deploy_backup/backup"
    os.system(cleanup_command)


def execute_restore_from_dir(pname):
    backup_dir = setup_backup_dir(pname)

    os.system("rm ./*.yaml")
    os.system("cp -v %s/*.yaml ." % backup_dir)
    os.system("mkdir -p ./deploy/sshkey")
    os.system("mkdir -p ./deploy/ssl")
    os.system("cp -r %s/sshkey/* ./deploy/sshkey" % backup_dir)
    # Make ssh for the current user work
    os.system("chmod 600 ./deploy/sshkey/id_rsa")
    if os.path.exists("%s/ssl/kubelet" % backup_dir):
        os.system("cp -r %s/ssl/* ./deploy/ssl" % backup_dir)
    os.system("cp %s/clusterID/*.yml ./deploy/" % backup_dir)
    if os.path.exists("%s/acs_kubeclusterconfig" % backup_dir):
        os.system("cp -r %s/acs_kubeclusterconfig ./deploy/" % backup_dir)


def backup_keys(clusterName, nargs=[]):
    if len(nargs) <= 0:
        clusterID = get_cluster_ID_from_file()
        fname = "./deploy_backup/config=%s-%s=%s-%s" % (
            clusterName, clusterID, str(time.time()), str(uuid.uuid4())[:5])
        key = None
    else:
        fname = nargs[0]
        if len(nargs) <= 1:
            key = None
        else:
            key = nargs[1]

    execute_backup_and_encrypt(clusterName, fname, key)


def backup_keys_to_dir(nargs):
    assert len(nargs) > 0
    pname = nargs[0]
    execute_backup_to_dir(pname)


def restore_keys(nargs):
    if len(nargs) <= 0:
        list_of_files = glob.glob("./deploy_backup/config*")
        fname = max(list_of_files, key=os.path.getctime)
        key = None
    else:
        fname = nargs[0]
        if len(nargs) <= 1:
            key = None
        else:
            key = nargs[1]
    execute_restore_and_decrypt(fname, key)


def restore_keys_from_dir(nargs):
    assert len(nargs) > 0
    pname = nargs[0]
    execute_restore_from_dir(pname)


def getIP(dnsname):
    try:
        data = socket.gethostbyname(dnsname)
        ip = repr(data).replace("'", "")
        return ip
    except Exception:
        return None


def addressInNetwork(ip, net):
    "Is an address in a network"
    ret = False
    try:
        ipaddr = struct.unpack('!I', socket.inet_aton(ip))[0]
        netaddr, bits = net.split('/')
        netmask = struct.unpack('!I', socket.inet_aton(netaddr))[0] & (
            (2 << int(bits) - 1) - 1)
        ret = ipaddr & netmask == netmask
    except Exception as e:
        ret = False
    return ret


class ValClass:
    def __init__(self, initVal):
        self.val = initVal

    def set(self, newVal):
        self.val = newVal


def shellquote(s):
    return "'" + s.replace("'", "'\\''") + "'"


def tryuntil(cmdLambda, stopFn, updateFn, waitPeriod=5):
    while not stopFn():
        try:
            output = cmdLambda(
            ) # if exception occurs here, update does not occur
            #print "Output: {0}".format(output)
            updateFn()
            toStop = False
            try:
                toStop = stopFn()
            except Exception as e:
                print("Exception {0} -- stopping anyways".format(e))
                toStop = True
            if toStop:
                #print "Returning {0}".format(output)
                return output
        except Exception as e:
            print("Exception in command {0}".format(e))
        if not stopFn():
            print("Not done yet - Sleep for 5 seconds and continue")
            time.sleep(waitPeriod)


# Run until stop condition and success


def subproc_tryuntil(cmd, stopFn, shell=True, waitPeriod=5):
    bFirst = ValClass(True)
    return tryuntil(lambda: subprocess.check_output(cmd, shell),
                    lambda: not bFirst.val and stopFn(),
                    lambda: bFirst.set(False), waitPeriod)


def subprocrun(cmd, shellArg):
    #print "Running Cmd: {0} Shell: {1}".format(cmd, shellArg)
    # embed()
    return subprocess.check_output(cmd, shell=shellArg)


# Run once until success (no exception)


def subproc_runonce(cmd, shell=True, waitPeriod=5):
    bFirst = ValClass(True)
    #print "Running cmd:{0} Shell:{1}".format(cmd, shell)
    return tryuntil(lambda: subprocrun(cmd, shell), lambda: not bFirst.val,
                    lambda: bFirst.set(False), waitPeriod)


# Run for N success


def subproc_runN(cmd, n, shell=True, waitPeriod=5):
    bCnt = ValClass(0)
    return tryuntil(lambda: subprocess.check_output(cmd, shell), lambda:
                    (bCnt.val < n), lambda: bCnt.set(bCnt.val + 1), waitPeriod)


def mergeDict(configDst, configSrc, bOverwrite):
    for entry in configSrc:
        # if not isinstance(configSrc[entry], dict):
        #     print "key:{0} val:{1}".format(entry, configSrc[entry])
        if bOverwrite:
            configDst.pop(entry, None)
        if (not entry in configDst) or (configDst[entry] is None) or \
                (isinstance(configDst[entry], str) and configDst[entry].lower() == "null"):
            if isinstance(configSrc[entry], dict):
                configDst[entry] = {}
                mergeDict(configDst[entry], configSrc[entry], bOverwrite)
            else:
                #print "settingkey:{0} val:{1}".format(entry, configSrc[entry])
                configDst[entry] = configSrc[entry]
        elif isinstance(configSrc[entry], dict) and isinstance(
                configDst[entry], dict):
            mergeDict(configDst[entry], configSrc[entry], bOverwrite)


def ip2int(addr):
    return struct.unpack("!I", socket.inet_aton(addr))[0]


def mask_num(valid_bit):
    return int('1' * valid_bit + '0' * (32 - valid_bit), 2)


def remain_num(valid_bit):
    return int('0' * valid_bit + '1' * (32 - valid_bit), 2)


def check_covered_by_ipvals(ipvals, masked2check):
    for wider_ipval in ipvals:
        if wider_ipval == masked2check:
            return True
    return False


def check_covered_by_wider_ips(mask2ip, ipval2check, mask4ipval):
    for msk in list(mask2ip.keys()):
        # wider mask range
        if msk < mask4ipval:
            this_masked = ipval2check & mask_num(msk)
            if check_covered_by_ipvals(mask2ip[msk], this_masked):
                return True
    return False


def keep_widest_subnet(ips):
    res = set()
    mask2ip = {}
    ips = sorted(ips, key=lambda x: int(x[-2:]))
    for ip in ips:
        ipv4, mask = ip.split("/")
        mask = int(mask)
        ipval = ip2int(ipv4)
        remnmsk = remain_num(mask)
        assert (remnmsk & ipval == 0), "invalid ip/mask {}!".format(ip)
        if check_covered_by_wider_ips(mask2ip, ipval, mask):
            continue
        if mask not in mask2ip:
            mask2ip[mask] = set()
        mask2ip[mask].add(ipval)
        res.add(ip)
    return list(res)


def random_str(length):
    return ''.join(random.choice(string.ascii_lowercase) for x in range(length))


def multiprocess_exec(func, args_list, process_num):
    pool = Pool(process_num)
    pool.map(func, args_list)
    pool.close()


def walk_json(obj, *fields, default=None):
    """ for example a=[{"a": {"b": 2}}]
    walk_json(a, 0, "a", "b") will get 2
    walk_json(a, 0, "not_exist") will get None
    """
    try:
        for f in fields:
            obj = obj[f]
        return obj
    except:
        return default


class RestUtil(object):
    def __init__(self, rest_url):
        self.rest_url = rest_url

    def get_resource_quota(self, username):
        args = urllib.parse.urlencode({"userName": username})
        url = urllib.parse.urljoin(self.rest_url, "/ResourceQuota") + "?" + args
        resp = requests.get(url)
        return resp.json()

    def update_resource_quota(self, username, payload):
        args = urllib.parse.urlencode({"userName": username})
        url = urllib.parse.urljoin(self.rest_url, "/ResourceQuota") + "?" + args
        resp = requests.post(url, json=payload)
        return resp.json()
