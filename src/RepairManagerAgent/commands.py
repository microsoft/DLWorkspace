import os

def reboot_node():
    os.system('sync')
    os.system('reboot -f')
