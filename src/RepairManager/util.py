import os

def cordon_node(node):
    output = os.system('kubectl cordon %s --dry-run' % node)
    return output

