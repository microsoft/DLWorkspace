#!/usr/bin/python 
# Automatic monitoring mount process
import time
import os
from datetime import datetime
import yaml
import logging
import logging.config
import argparse
import textwrap
import socket
import subprocess
import re
import sys

def start_logging( logdir = '/var/log/auto_share' ):
	if not os.path.exists( logdir ):
		os.system("sudo mkdir -p " + logdir )
	with open('logging.yaml') as f:
		logging_config = yaml.load(f)
		f.close()
		# print logging_config
		logging.config.dictConfig(logging_config)
	logging.debug (".................... Start auto_share at %s .......................... " % datetime.now() )
	logging.debug ( "Argument : %s" % sys.argv )

if __name__ == '__main__':
	parser = argparse.ArgumentParser( prog='auto_share.py',
		formatter_class=argparse.RawDescriptionHelpFormatter,
		description=textwrap.dedent('''\
Automatically monitor and mount file share. 
  ''') )
	parser.add_argument('nargs', nargs=argparse.REMAINDER, 
		help="Additional command argument", 
		)
	dir_path = os.path.dirname(os.path.realpath(__file__))
	os.chdir(dir_path)
	args = parser.parse_args()
	
	start_logging()
	logging.debug( "End auto_share ... " )

