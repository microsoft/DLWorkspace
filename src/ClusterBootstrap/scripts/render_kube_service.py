#!/usr/bin/python3
import sys
import yaml
import jinja2
import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='cloud_init_deploy.py',
             formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-nt', '--node_types', nargs='+', help='Specify the node types \
        whose services we would label to the node executing this script')
    parser.add_argument('-t', '--template', default='kubelet.service.template', help='Path of template file')
    parser.add_argument('-r', '--rendered', default='kubelet.service', help='Path of rendered file')
    args = parser.parse_args()
    template_env = jinja2.Environment(loader=jinja2.FileSystemLoader('./'))
    labels = []
    for svc_type in args.node_types:
        with open(svc_type+"_labels.yaml") as sf:
            try:
                labels += yaml.safe_load(sf)
            except:
                print("Warning: failed to load " + svc_type+"_labels.yaml")
    config = {'labels':list(set(labels))}
    with open(args.rendered, 'w') as fw:
        tpl = template_env.get_template(args.template)
        content = tpl.render(cnf=config)
        fw.write(content)