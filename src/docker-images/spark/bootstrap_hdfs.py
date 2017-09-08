#!/usr/bin/python
import argparse
import textwrap
import socket
import os
import subprocess
import logging
import logging.config
import logutils.dictconfig
import yaml
from jinja2 import Environment, FileSystemLoader, Template
import utils

verbose = True

def create_log( logdir ):
    if not os.path.exists( logdir ):
        os.system("mkdir -p " + logdir )

def exec_with_output( cmd ):
    try:
        # https://stackoverflow.com/questions/4814970/subprocess-check-output-doesnt-seem-to-exist-python-2-6-5                
        print cmd
        output = subprocess.Popen( cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT ).communicate()[0]
        print output
    except subprocess.CalledProcessError as e:
        print "Exception " + str(e.returncode) + ", output: " + e.output.strip()

if __name__ == '__main__':
    print "Start... boostrap_hdfs.py "
    try:
        parser = argparse.ArgumentParser(prog='boostrap_hdfs.py',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description=textwrap.dedent('''\
Lauch a HDFS server.

Command: 
journalnode: Launch journal node. 
namenode:    Launch namenode. 
datanode:    Launch datanode. 
''') )
        parser.add_argument("--config", 
            help="configuration file", 
            action="store", 
            default="/etc/hdfs/config.yaml")
        parser.add_argument("-v", "--verbose", 
            help="verbose information", 
            action="store_true" )
        parser.add_argument("-f", "--force", 
            help="force (formatting)", 
            action="store_true" )

        parser.add_argument("server", help = "See above for the list of available server type" )
        # Obtain argument from environment variable. 
        args = parser.parse_args()
        verbose = args.verbose
        server = args.server
        print "Parse command line argument... "
        config_file = args.config
        if not os.path.exists(config_file):
            print "!!!Error!!! Can't find configuration file %s " % config_file
            parser.print_help()
        with open(config_file, 'r') as file:
            config = yaml.load(file)
        print "Configuration is : %s " % config
        loggingDirBase = "/var/log/hdfs" if not "loggingDirBase" in config else config["loggingDirBase"]
        config["loggingDir"] = os.path.join( loggingDirBase, server )
        utils.render_template("logging.yaml.in-docker", "logging.yaml",config, verbose=verbose)
#        logdir = config["loggingDir"]
#        create_log( logdir )
#        with open('logging.yaml') as f:
#           logging_config = yaml.load(f)
#           f.close()
#           print logging_config
#           logutils.dictconfig.dictConfig(logging_config)
        isHA = "namenode2" in config["namenode"]
        if isHA:
            utils.render_template("hdfs-site.xml.in-docker", "/usr/local/hadoop/etc/hadoop/hdfs-site.xml",config, verbose=verbose)
        else:
            utils.render_template("hdfs-site-single.xml.in-docker", "/usr/local/hadoop/etc/hadoop/hdfs-site.xml",config, verbose=verbose)
        utils.render_template("mapred-site.xml.in-docker", "/usr/local/hadoop/etc/hadoop/mapred-site.xml",config, verbose=verbose)
        if isHA:
            utils.render_template("yarn-site.xml.in-docker", "/usr/local/hadoop/etc/hadoop/yarn-site.xml",config, verbose=verbose)
        else:
            utils.render_template("yarn-site-single.xml.in-docker", "/usr/local/hadoop/etc/hadoop/yarn-site.xml",config, verbose=verbose)
    except Exception as e:
        print "boostrap_hdfs.py fails during initialization, exception %s" % e
        exit()
    # Launch journal node
    if server == "journalnode":
        cmd = "/usr/local/hadoop/sbin/hadoop-daemon.sh start journalnode"
        exec_with_output( cmd )
        exec_with_output( "pgrep -f JournalNode")
        print "JournalNode running .... "
    elif server == "zookeeper":
        cmd = "/usr/local/hadoop/sbin/hadoop-daemon.sh start zookeeper"
        exec_with_output( cmd )
        print "Zookeeper node is running .... "
    elif server == "namenode":
        cmd = "/usr/local/hadoop/sbin/hadoop-daemon.sh start namenode"
        exec_with_output( cmd )
        cmd = "/usr/local/hadoop/sbin/hadoop-daemon.sh start zkfc"
        exec_with_output( cmd )
        exec_with_output( "pgrep -f NameNode")
        exec_with_output( "pgrep -f DFSZKFailoverController")
        print "Namenode is running"
    elif server == "datanode":
        cmd = "/usr/local/hadoop/sbin/hadoop-daemon.sh start datanode"
        exec_with_output( cmd )
        exec_with_output( "pgrep -f DataNode")
        print "Datanode is running"
    elif server == "format":
        force = "" if not args.force else "-force "
        cmd = "/usr/local/hadoop/bin/hdfs namenode -format %s -nonInteractive" % force
        exec_with_output( cmd )
        if isHA:
            cmd = "/usr/local/hadoop/bin/hdfs zkfc -formatZK -nonInteractive"
            exec_with_output( cmd )
        print "Format namenode and zkfc ..... "
        if isHA:
            remotedir = os.path.join( config["namenode"]["data"], "current")
            localdir = os.path.join( config["namenode"]["localdata"], "current")
            exec_with_output( "rm -rf %s" % remotedir )
            exec_with_output( "cp -r %s %s" % ( localdir, remotedir ) )
            print "Copy data from %s to %s" % ( localdir, remotedir )
    elif server == "copy":
        remotedir = os.path.join( config["namenode"]["data"], "current")
        localdir = os.path.join( config["namenode"]["localdata"], "current")
        exec_with_output( "cp -r %s %s" % ( localdir, remotedir ) )
        print "Copy data from %s to %s" % ( localdir, remotedir )
    elif server == "standby":
        remotedir = os.path.join( config["namenode"]["data"], "current")
        localdir = os.path.join( config["namenode"]["localdata"], "current")
        exec_with_output( "cp -r %s %s" % ( remotedir, localdir ) )
        print "Copy data from %s to %s" % ( remotedir, localdir )
    elif server == "resourcemanager":
        cmd = "/usr/local/hadoop/sbin/yarn-daemon.sh start resourcemanager"
        exec_with_output( cmd )
        cmd1 = "/usr/local/hadoop/sbin/mr-jobhistory-daemon.sh start historyserver"
        exec_with_output( cmd1 )
        exec_with_output( "pgrep -f DataNode")
        print "Yarn resource manager and history server is running"
    elif server == "nodemanager":
        cmd = "/usr/local/hadoop/sbin/yarn-daemon.sh start nodemanager"
        exec_with_output( cmd )
        exec_with_output( "pgrep -f DataNode")
        print "Yarn node manager is running"
    elif server == "spark":
        print "Ready to execute spark command. "
    else:
        print "Unknown server" + server


