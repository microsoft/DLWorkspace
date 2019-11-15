import os
import sys
import argparse
import logging

from datetime import datetime, timedelta

DATETIME_FMT = "%Y/%m/%d %H:%M:%S"


class PathNode(object):
    def __init__(self,
                 path,
                 isdir,
                 size,
                 atime,
                 children=None):
        self.path = path
        self.isdir = isdir
        self.size = size
        self.subtree_size = size
        self.atime = atime
        self.children = []
        if isinstance(children, list):
            self.children = children
        self.num_subtree_nodes = 1

    def __str__(self):
        path_type = "Directory" if self.isdir else "File"
        return "%s %s: size %d, subtree_size %d, atime %s" % \
               (path_type,
                self.path,
                self.size,
                self.subtree_size,
                self.atime.strftime(DATETIME_FMT))


def create_node(node_path):
    node_stat = os.stat(node_path)
    node_isdir = os.path.isdir(node_path)
    node_size = node_stat.st_size
    node_atime = datetime.fromtimestamp(node_stat.st_atime)
    node = PathNode(path=node_path,
                    isdir=node_isdir,
                    size=node_size,
                    atime=node_atime)
    return node


def create_tree(root):
    if os.path.islink(root):
        return None

    try:
        pathnames = os.listdir(root)
    except Exception as e:
        logging.warn("Ignore path %s due to exception %s" % (root, e))
        return None

    root_node = create_node(root)

    dirs, nondirs = [], []
    for pathname in pathnames:
        path = os.path.join(root, pathname)
        if os.path.islink(path):
            continue

        if os.path.isdir(path):
            dirs.append(pathname)
        else:
            nondirs.append(pathname)

    for pathname in dirs:
        child_dir = os.path.join(root, pathname)
        child_dir_node = create_tree(child_dir)
        if child_dir_node is not None:
            root_node.children.append(child_dir_node)
            root_node.subtree_size += child_dir_node.subtree_size
            root_node.num_subtree_nodes += child_dir_node.num_subtree_nodes

    for pathname in nondirs:
        child_file = os.path.join(root, pathname)
        path_node = create_node(child_file)
        root_node.children.append(path_node)
        root_node.subtree_size += path_node.subtree_size
        root_node.num_subtree_nodes += path_node.num_subtree_nodes

    return root_node


def print_tree_preorder(root):
    if root is None:
        return

    logging.info(root)

    for child in root.children:
        print_tree_preorder(child)


def find_overweight_nodes(root, threshold):
    if root is None:
        return []

    if not root.isdir:
        if root.subtree_size > threshold:
            return [root]

    if root.subtree_size <= threshold:
        return []

    overweight_nodes = []

    if root.subtree_size > threshold:
        overweight_nodes.append(root)

    for child in root.children:
        overweight_nodes += find_overweight_nodes(child, threshold)

    return overweight_nodes


def find_expired_nodes(root, expiry):
    if root is None:
        return []

    expired_nodes = []

    if root.atime < expiry:
        expired_nodes.append(root)

    for child in root.children:
        expired_nodes += find_expired_nodes(child, expiry)

    return expired_nodes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", default=".", type=str)
    parser.add_argument("--threshold", default=4096, type=int,
                        help="Path with size greater than the threshold is "
                             "considered overweight")
    parser.add_argument("--expiry", default=31, type=int,
                        help="Expiry is the number of days before a path is "
                             "considered expired")

    args, _ = parser.parse_known_args()
    path = args.path
    threshold = args.threshold
    expiry = datetime.now() - timedelta(days=args.expiry)

    logging.info("Creating tree rooted at %s starts." % path)
    root = create_tree(path)
    logging.info("Creating tree rooted at %s finishes." % path)

    logging.info("Total number of paths found: %d" % root.num_subtree_nodes)

    #print_tree_preorder(root)
    overweight_nodes = find_overweight_nodes(root, threshold)
    logging.info("Overweight (> %d) paths are:" % threshold)
    for node in overweight_nodes:
        logging.info("%16d  %s" % (node.subtree_size, node.path))

    expired_nodes = find_expired_nodes(root, expiry)
    logging.info("Expired (access time < %s) paths are:" %
                 expiry.strftime(DATETIME_FMT))
    for node in expired_nodes:
        logging.info("%s  %s" % (node.atime.strftime(DATETIME_FMT), node.path))


if __name__ == "__main__":
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter("[%(levelname)s %(asctime)s] %(message)s")
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    main()
