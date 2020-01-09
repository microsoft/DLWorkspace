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
    def __init__(self, config, uid_user=None):
        """Constructs a PathTree object.

        Args:
            config: Configuration for creating PathTree.
            uid_user: UID -> user mapping
        """
        self.logger = logging.getLogger()
        self.path = config["path"]
        self.overweight_threshold = config["overweight_threshold"]
        self.expiry = datetime.fromtimestamp(config["now"]) - \
            timedelta(days=config["expiry_days"])

        self.uid_user = uid_user

        self.root = None

        self.overweight_boundary_nodes = []
        self.expired_boundary_nodes = []
        self.empty_boundary_nodes = []

    def walk(self):
        """Traverse filesystem tree and find desired nodes."""
        if self.path is None or not os.path.exists(self.path):
            self.logger.warning("Path %s is invalid. Skip walking.", self.path)

        self.root = self._walk(self.path)

    def _walk(self, root):
        if root != self.path and os.path.islink(root):
            # Allow tree root to be a link
            return None

        try:
            pathnames = os.listdir(root)
        except Exception as e:
            self.logger.warning("Ignore path %s due to exception %s", root, e)
            return None

        root_node = PathNode(root, uid_user=self.uid_user)

        dirs, nondirs = [], []
        for pathname in pathnames:
            path = os.path.join(root, pathname)
            if os.path.islink(path):
                continue

            if os.path.isdir(path):
                dirs.append(pathname)
            else:
                nondirs.append(pathname)

        children = []
        for pathname in dirs:
            child_dir = os.path.join(root, pathname)
            child_dir_node = self._walk(child_dir)
            if child_dir_node is not None:
                children.append(child_dir_node)
                root_node.subtree_size += child_dir_node.subtree_size
                if child_dir_node.subtree_atime > root_node.subtree_atime:
                    root_node.subtree_atime = child_dir_node.subtree_atime
                if child_dir_node.subtree_mtime > root_node.subtree_mtime:
                    root_node.subtree_mtime = child_dir_node.subtree_mtime
                if child_dir_node.subtree_ctime > root_node.subtree_ctime:
                    root_node.subtree_ctime = child_dir_node.subtree_ctime
                root_node.num_subtree_nodes += child_dir_node.num_subtree_nodes
                root_node.num_subtree_files += child_dir_node.num_subtree_files

        for pathname in nondirs:
            child_file = os.path.join(root, pathname)
            path_node = PathNode(child_file, uid_user=self.uid_user)
            children.append(path_node)
            root_node.subtree_size += path_node.subtree_size
            if path_node.subtree_atime > root_node.subtree_atime:
                root_node.subtree_atime = path_node.subtree_atime
            if path_node.subtree_mtime > root_node.subtree_mtime:
                root_node.subtree_mtime = path_node.subtree_mtime
            if path_node.subtree_ctime > root_node.subtree_ctime:
                root_node.subtree_ctime = path_node.subtree_ctime
            root_node.num_subtree_nodes += path_node.num_subtree_nodes
            root_node.num_subtree_files += path_node.num_subtree_files

        if root_node.subtree_size > self.overweight_threshold:
            all_children_underweight = True
            for child in children:
                if child.subtree_size > self.overweight_threshold:
                    all_children_underweight = False
                    if not child.isdir:
                        self.overweight_boundary_nodes.append(child)
            if all_children_underweight:
                self.overweight_boundary_nodes.append(root_node)

        if root_node.subtree_atime > self.expiry:
            for child in children:
                if child.subtree_atime < self.expiry:
                    self.expired_boundary_nodes.append(child)

        if root_node.num_subtree_files > 0:
            for child in children:
                if child.num_subtree_files == 0:
                    self.empty_boundary_nodes.append(child)

        return root_node
