import os

from datetime import datetime


DATETIME_FMT = "%Y/%m/%d %H:%M:%S"
K = 1.0 * 2 ** 10
M = 1.0 * 2 ** 20
G = 1.0 * 2 ** 30

DAY = 86400


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
        self.uid = stat.st_uid
        self.gid = stat.st_gid

        self.owner = ""
        if isinstance(uid_user, dict):
            self.owner = uid_user.get(self.uid, "")

        self.num_subtree_nodes = 1

        self.children = []

    def __str__(self):
        """Returns PathNode string in format atime,size,owner,path."""
        node_info = "%s,%dG,%s,%s" % (
            self.subtree_atime.strftime(DATETIME_FMT),
            self.subtree_size / G,
            self.owner,
            self.path)
        return node_info
