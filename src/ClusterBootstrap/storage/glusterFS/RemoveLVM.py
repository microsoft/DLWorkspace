#!/opt/bin/python 
# Remove leftover volume deployed by glusterFS
import os
import subprocess

if __name__ == '__main__':
    try:
        output = subprocess.check_output( "sudo lvdisplay", shell=True )
    except subprocess.CalledProcessError as e:
        print "Execution failed: " + e.output
        output = "Execution failed: " + e.output
        exit()
    lines = output.split("\n")
    for line in lines:
        segs = line.split()
        if len(segs) >= 2 and segs[0]=="VG NAME":
            os.system("sudo lvremove -f "+segs[1])
            print "Remove volume: " + segs[1]

