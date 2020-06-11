import os
import logging
import collections

from path_node import PathNode
from datetime import datetime, timedelta


def get_alias(user):
    if user == "":
        return "N/A"
    return user.split("@")[0]


class PathTree(object):
    """This class implements a tree of file system PathNode.

    Attributes:
        logger: Logging tool.
        path: Root path for the tree.
        overweight_threshold: The threshold of overweight nodes.
        expiry: Nodes are expired if either of the below is true:
            - node is a file, and both atime and mtime are earlier than this
            - node is a directory, and mtime is earlier than this
        root: Tree root that holds the file system PathTree.
    """
    def __init__(self, config, uid_to_user=None):
        """Constructs a PathTree object.

        Args:
            config: Configuration for creating PathTree.
            uid_to_user: UID -> user mapping
        """
        self.logger = logging.getLogger()
        self.path = config["path"]
        self.overweight_threshold = config["overweight_threshold"]
        self.expiry = datetime.fromtimestamp(config["now"]) - \
            timedelta(days=int(config["expiry_days"]))
        self.expiry_delete = None
        if config.get("days_to_delete_after_expiry") is not None:
            expiry_delete_days = int(config["expiry_days"]) + \
                                 int(config["days_to_delete_after_expiry"])
            self.expiry_delete = datetime.fromtimestamp(config["now"]) - \
                timedelta(days=expiry_delete_days)

        self.uid_to_user = uid_to_user

        self.root = None

        self.hardlink_ino = set()

        # Record storage usage by user. user alias -> usage in bytes
        self.usage_by_user = collections.defaultdict(lambda: 0)

        self.overweight_boundary_nodes = []
        self.expired_boundary_nodes = []
        self.expired_boundary_nodes_to_delete = []
        self.empty_boundary_nodes = []

    def walk(self):
        """Traverse filesystem tree and find desired nodes."""
        if self.path is None or not os.path.exists(self.path):
            self.logger.warning("Path %s is invalid. Skip walking.", self.path)

        self.root = self._walk(self.path)

    def _not_hardlink(self, path_node):
        # Directory can never be a hardlink
        # Files with #links == 1 is not a hardlink
        return path_node.isdir or path_node.nlink == 1

    def _new_hardlink(self, path_node):
        # Assumes path_node is a hardlink
        if path_node.ino in self.hardlink_ino:
            return False

        self.hardlink_ino.add(path_node.ino)
        return True

    def _walk(self, root):
        if root != self.path and os.path.islink(root):
            # Allow tree root to be a link
            return None

        try:
            root_node = PathNode(root, uid_to_user=self.uid_to_user)
            self.usage_by_user[get_alias(root_node.owner)] += root_node.size
        except:
            self.logger.warning("Ignore path %s due to exception",
                                root,
                                exc_info=True)
            return None

        try:
            pathnames = os.listdir(root)
        except:
            self.logger.warning("Ignore path %s due to exception",
                                root,
                                exc_info=True)
            return None

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
                if child_dir_node.subtree_time > root_node.subtree_time:
                    root_node.subtree_time = child_dir_node.subtree_time
                root_node.num_subtree_nodes += child_dir_node.num_subtree_nodes
                root_node.num_subtree_files += child_dir_node.num_subtree_files

        for pathname in nondirs:
            child_file = os.path.join(root, pathname)
            try:
                path_node = PathNode(child_file, uid_to_user=self.uid_to_user)
                self.usage_by_user[get_alias(path_node.owner)] += path_node.size
            except:
                continue
            children.append(path_node)
            # do not count hardlink twice if any
            if self._not_hardlink(path_node) or self._new_hardlink(path_node):
                root_node.subtree_size += path_node.subtree_size
            if path_node.subtree_atime > root_node.subtree_atime:
                root_node.subtree_atime = path_node.subtree_atime
            if path_node.subtree_mtime > root_node.subtree_mtime:
                root_node.subtree_mtime = path_node.subtree_mtime
            if path_node.subtree_ctime > root_node.subtree_ctime:
                root_node.subtree_ctime = path_node.subtree_ctime
            if path_node.subtree_time > root_node.subtree_time:
                root_node.subtree_time = path_node.subtree_time
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

        if root_node.subtree_time >= self.expiry:
            for child in children:
                if child.subtree_time < self.expiry:
                    self.expired_boundary_nodes.append(child)

        if self.expiry_delete is not None:
            if root_node.subtree_time >= self.expiry_delete:
                for child in children:
                    if child.subtree_time < self.expiry_delete:
                        self.expired_boundary_nodes_to_delete.append(child)

        if root_node.num_subtree_files > 0:
            for child in children:
                if child.num_subtree_files == 0:
                    self.empty_boundary_nodes.append(child)

        return root_node
