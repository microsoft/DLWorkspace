#!/usr/bin/python 
# launch gluster fs 
import time
from datetime import datetime

curtime = datetime.utcnow()
# set up logging to file - see previous section for more details
print "Start glusterfs ...." 




if __name__ == '__main__':
	while True:
		print "Keep container alive, time ... " + str(datetime.utcnow()) 
		time.sleep(5)

