import os
import logging

from path_node import PathNode
from datetime import datetime, timedelta


class PathTree(object):
    """This class implements a tree of file system PathNode.

    Attributes:
        logger: Logging tool.
        path: Root path for the tree.
        overweight_threshold: The threshold of overweight nodes.
        expiry: Nodes are expired if access time is earlier than this.
        root: Tree root that holds the file system PathTree.
    """
    def __init__(self, config):
        """Constructs a PathTree object.

        Args:
            config: Configuration for creating PathTree.
        """
        self.logger = logging.getLogger()
        self.path = config["path"]
        self.overweight_threshold = config["overweight_threshold"]
        self.expiry = datetime.fromtimestamp(config["now"]) - \
                      timedelta(days=config["expiry_days"])

        self.root = None

    def create_tree(self):
        """Creates a tree for the root path."""
        self.logger.info("Creating tree for path %s" % self.path)
        self.root = self._create_tree(self.path)
        self.logger.info("Successfully created tree for path %s" % self.path)

    def print_tree_preorder(self):
        """Prints the tree using preorder traversal"""
        self._print_tree_preorder(self.root)

    def find_overweight_nodes(self):
        """Returns the overweight nodes."""
        return self._find_overweight_nodes(self.root,
                                           self.overweight_threshold)

    def find_expired_nodes(self):
        """Returns the expired nodes."""
        return self._find_expired_nodes(self.root, self.expiry)

    def _create_tree(self, root):
        if root != self.path and os.path.islink(root):
            # Allow root to be a link
            return None

        try:
            pathnames = os.listdir(root)
        except Exception as e:
            self.logger.warning("Ignore path %s due to exception %s" % (root, e))
            return None

        root_node = PathNode(root)

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
            child_dir_node = self._create_tree(child_dir)
            if child_dir_node is not None:
                root_node.children.append(child_dir_node)
                root_node.subtree_size += child_dir_node.subtree_size
                if child_dir_node.subtree_atime > root_node.subtree_atime:
                    root_node.subtree_atime = child_dir_node.subtree_atime
                root_node.num_subtree_nodes += child_dir_node.num_subtree_nodes

        for pathname in nondirs:
            child_file = os.path.join(root, pathname)
            path_node = PathNode(child_file)
            root_node.children.append(path_node)
            root_node.subtree_size += path_node.subtree_size
            if path_node.subtree_atime > root_node.subtree_atime:
                root_node.subtree_atime = path_node.subtree_atime
            root_node.num_subtree_nodes += path_node.num_subtree_nodes

        return root_node

    def _print_tree_preorder(self, root):
        if root is None:
            return

        print(root)

        for child in root.children:
            self._print_tree_preorder(child)

    def _find_overweight_nodes(self, root, thres):
        if root is None:
            return []

        if not root.isdir:
            if root.subtree_size > thres:
                return [root]

        if root.subtree_size <= thres:
            return []

        overweight_nodes = []

        if root.subtree_size > thres:
            overweight_nodes.append(root)

        for child in root.children:
            overweight_nodes += self._find_overweight_nodes(child, thres)

        return overweight_nodes

    def _find_expired_nodes(self, root, expiry):
        if root is None:
            return []

        expired_nodes = []

        if root.subtree_atime < expiry:
            expired_nodes.append(root)

        for child in root.children:
            expired_nodes += self._find_expired_nodes(child, expiry)

        return expired_nodes
