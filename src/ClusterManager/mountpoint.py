#!/usr/bin/env python3

import logging
import logging.config
import re

logger = logging.getLogger(__name__)
REG = r"(.*?)_([a-zA-Z])"


def camel_case(match):
    return match.group(1) + match.group(2).upper()


def camel(s):
    return re.sub(REG, camel_case, s, 0)


def override(func):
    return func


def normalize(s):
    return "".join([c for c in s if c.isalnum() or c == "-"]).lower()


class MountPoint(object):
    """MountPoints are for a job. They must not have the same name or same
    mount path.
    """
    subclasses = {}

    def __init__(self, params):
        self.mount_path = None
        self.mount_type = None
        self.sub_path = None
        self.vc = None
        self.name = None
        self.enabled = True

        if isinstance(params, dict):
            for k, v in self.__dict__.items():
                if v is None:
                    self.__dict__[k] = params.get(camel(k))

        if self.name is None:
            vc_prefix = "" if self.vc is None else "%s-" % self.vc
            self.name = "%s%s" % (vc_prefix, self.mount_path)
        self.name = normalize(self.name)

    @classmethod
    def register_subclass(cls, mount_type):
        def decorator(subclass):
            cls.subclasses[mount_type] = subclass
            return subclass

        return decorator

    @classmethod
    def create(cls, mount_type, params):
        if mount_type not in cls.subclasses:
            raise ValueError("Bad mountType %s" % mount_type)
        return cls.subclasses[mount_type](params)

    @override
    def is_valid(self):
        return self.mount_path is not None and \
               self.mount_type is not None and \
               self.name is not None

    @override
    def __eq__(self, other):
        # A job cannot tolerate identical mountpoint names
        if self.name == other.name:
            return True

        # A job cannot tolerate identical mount paths
        if self.mount_path.strip("/") == other.mount_path.strip("/"):
            return True

        if self.__class__ != other.__class__:
            return False

        for k in self.__dict__:
            if self.__dict__[k] != other.__dict__[k]:
                return False

        return True

    def to_dict(self):
        ret = {camel(k): v for k, v in self.__dict__.items() if v is not None}
        return ret

    def __repr__(self):
        return "%s" % self.to_dict()

    def disable(self):
        self.enabled = False

    def enable(self):
        self.enabled = True


@MountPoint.register_subclass("hostPath")
class HostPathMountPoint(MountPoint):
    def __init__(self, params):
        self.host_path = None
        self.type = None
        super(HostPathMountPoint, self).__init__(params)

    def is_valid(self):
        return self.host_path is not None and \
               super(HostPathMountPoint, self).is_valid()


@MountPoint.register_subclass("nfs")
class NFSMountPoint(MountPoint):
    def __init__(self, params):
        self.server = None
        self.path = None
        super(NFSMountPoint, self).__init__(params)

    def is_valid(self):
        return self.server is not None and \
               self.path is not None and \
               super(NFSMountPoint, self).is_valid()


@MountPoint.register_subclass("blobfuse")
class BlobfuseMountPoint(MountPoint):
    def __init__(self, params):
        self.secreds = None
        self.container_name = None
        self.mount_options = None
        self.root_tmppath = None
        self.tmppath = None
        super(BlobfuseMountPoint, self).__init__(params)

    def is_valid(self):
        return self.secreds is not None and \
               self.container_name is not None and \
               super(BlobfuseMountPoint, self).is_valid()


def make_mountpoint(params):
    mountpoint = None
    try:
        mount_type = params.get("mountType", "hostPath")
        mountpoint = MountPoint.create(mount_type, params)
    except ValueError:
        logger.exception("Bad mountType in params %s", params, exc_info=True)
    except Exception:
        logger.exception("Exception in creating mountpoint with params %s",
                         params,
                         exc_info=True)
    return mountpoint
