import os

from datetime import datetime
from utils import DATETIME_FMT, bytes2human_readable


class PathNode(object):
    """This class contains meta info for a file/directory.

    Attributes:
        path: Path string for this node.
        isdir: Whether this node is a directory.
        size: Size of the node itself.
        subtree_size: Size of the subtree rooted at this node.
        atime: Access time of this node.
        subtree_atime: Access time of the subtree rooted at this node.
            Latest access time of the nodes in the subtree.
        mtime: Modification time of this node.
        subtree_mtime: Modification time of the subtree rooted at this node.
            Latest modification time of the nodes in the subtree.
        ctime: Permission change time of this node.
        subtree_ctime: Permission change time of the subtree rooted at this
            node. Latest permission change time of the nodes in the subtree.
        uid: User ID for this node.
        gid: Group ID for this node.
        owner: Username for this node.
        children: A list of child nodes of this node.
        num_subtree_nodes: Number of nodes in the subtree including itself.
    """
    def __init__(self, path, uid_user=None):
        """Constructs PathNode.

        Args:
            path: Path string for the node.
            uid_user: uid -> user mapping.
                When provided, it is used to look up username from uid.
        """
        self.path = path
        self.isdir = os.path.isdir(path)

        stat = os.stat(path)
        self.size = stat.st_size
        self.subtree_size = stat.st_size
        self.atime = datetime.fromtimestamp(stat.st_atime)
        self.subtree_atime = datetime.fromtimestamp(stat.st_atime)
        self.mtime = datetime.fromtimestamp(stat.st_mtime)
        self.subtree_mtime = datetime.fromtimestamp(stat.st_mtime)
        self.ctime = datetime.fromtimestamp(stat.st_ctime)
        self.subtree_ctime = datetime.fromtimestamp(stat.st_ctime)
        self.uid = stat.st_uid
        self.gid = stat.st_gid

        self.owner = ""
        if isinstance(uid_user, dict):
            self.owner = uid_user.get(self.uid, "")

        self.num_subtree_nodes = 1
        self.num_subtree_files = 0 if self.isdir else 1

        self.children = []

    def __str__(self):
        """Returns PathNode string in format atime,size,owner,path."""
        node_info = "%s,%s,%s,%s" % (
            self.subtree_atime.strftime(DATETIME_FMT),
            bytes2human_readable(self.subtree_size),
            self.owner,
            self.path)
        return node_info
