#!/usr/bin/python 
# launch gluster fs 
import time
import os
from datetime import datetime
import yaml
import logging
import logging.config

def create_log( logdir ):
	if not os.path.exists( logdir ):
		os.system("mkdir -p " + logdir )
	curtime = datetime.utcnow()
	fname = os.path.join( logdir, str(curtime) + ".log" )
	
def start_glusterfs( logdir = '/var/log/glusterfs/launch' ):
	with open('logging.yaml') as f:
		logging_config = yaml.load(f)
		f.close()
		logging.config.dictConfig(logging_config)
	create_log( logdir )
	# set up logging to file - see previous section for more details
	logging.debug ("Start launch glusterfs ...." )




if __name__ == '__main__':
	start_glusterfs()
	logging.debug( "End launch glusterfs, time ... " )

