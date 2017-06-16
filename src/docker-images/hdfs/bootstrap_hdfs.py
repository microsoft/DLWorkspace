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

verbose = False

def create_log( logdir ):
	if not os.path.exists( logdir ):
		os.system("mkdir -p " + logdir )

if __name__ == '__main__':
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

        parser.add_argument("server", help = "See above for the list of available server type" )
        # Obtain argument from environment variable. 
        args = parser.parse_args()
        verbose = args.verbose
        server = args.server
        config_file = args.config
        if not os.path.exists(config_file):
            print "!!!Error!!! Can't find configuration file %s " % config_file
            parser.print_help()
        with open(config_file, 'r') as file:
            config = yaml.load(file)
        if verbose: 
            print config
        loggingDirBase = "/var/log/hdfs" if not "loggingDirBase" in config else config["loggingDirBase"]
        config["loggingDir"] = os.path.join( loggingDirBase, server )
        utils.render_template("logging.yaml.in-docker", "logging.yaml",config, verbose=verbose)
        logdir = config["loggingDir"]
        create_log( logdir )
        with open('logging.yaml') as f:
	        logging_config = yaml.load(f)
	        f.close()
	        print logging_config
	        logutils.dictconfig.dictConfig(logging_config)
        utils.render_template("hdfs-site.xml.in-docker", "hdfs-site.xml",config, verbose=verbose)
    except Exception as e:
        print "boostrap_hdfs.py fails during initialization, exception %s" % e
        exit()
    

