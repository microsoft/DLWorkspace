#!/usr/bin/env python3
import os
import sys
import yaml
import argparse
import textwrap

def make_dir_and_cp(file_map_yaml, modules_list_str, user):
    modules_list = [mod for mod in modules_list_str.split(';') if mod]
    with open(file_map_yaml) as f:
        map_dict = yaml.safe_load(f)
    for mod in modules_list:
        if not mod in map_dict:
            print("Error: specified module {} not found.". format(mod))
            continue
        for itm in map_dict[mod]:
            dst_dir = os.path.dirname(itm["dst"])
            if not os.path.exists(dst_dir):
                os.system('sudo mkdir -p {}'.format(dst_dir))
                os.system('sudo chown -R {}:{} {}'.format(user, user, dst_dir))
            os.system('sudo cp -r {} {}'.format(itm["cld"], itm["dst"]))
            print("copied {} to {}".format(itm["cld"], itm["dst"]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='cloud_init_deploy.py',
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description=textwrap.dedent('''
        Copy files in cloud_init folder to destination path.

        Prerequest:
        * Have the cloudinit.tar downloaded on machine.

        Command:
            render  render all files from template
    '''))
    parser.add_argument("-u", "--user",
                        help="Username of the machine")
    parser.add_argument("-p", "--filemap",
                        help="Path of the filemap yaml")
    parser.add_argument('-m', '--module_list', default="", help='List of modules that we want to copy, split by semicolon')
    args = parser.parse_args()
    make_dir_and_cp(args.filemap, args.module_list, args.user)