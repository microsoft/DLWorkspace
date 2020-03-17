#!/usr/bin/env python3
import logging
import json
import requests
import random
import time
import threading

from DataHandler import DataHandler, DataManager
from config import config
from cachetools import cached, TTLCache

logger = logging.getLogger(__name__)


def enum(*sequential, **named):
    enums = dict(list(zip(sequential, list(range(len(sequential))))), **named)
    reverse = dict((value, key) for key, value in list(enums.items()))
    enums["reverse_mapping"] = reverse
    return type("Enum", (), enums)


Permission = enum(Unauthorized=0, User=1, Collaborator=3, Admin=7)
ResourceType = enum(Cluster=1, VC=2, Job=3)

INVALID_RANGE_START = 900000000
INVALID_ID = 999999999

INVALID_INFO = {"uid": INVALID_ID, "gid": INVALID_ID, "groups": [INVALID_ID]}

DEFAULT_CACHE_EXPIRATION = 30 * 60
DEFAULT_CACHE_SIZE = 10240
acl_cache = TTLCache(maxsize=DEFAULT_CACHE_SIZE, ttl=DEFAULT_CACHE_EXPIRATION)
acl_cache_lock = threading.Lock()

RESOURCE_KEY_PREFIX = "r/"
IDENTITY_KEY_PREFIX = "i/"
id_cache = TTLCache(maxsize=DEFAULT_CACHE_SIZE, ttl=DEFAULT_CACHE_EXPIRATION)
id_cache_lock = threading.Lock()


class AuthorizationManager:

    CLUSTER_ACL_PATH = "Cluster"
    ACL_DELIMITER = "/"
    TYPE_NAME_DELIMITER = ":"

    @staticmethod
    def _has_access(name, resource, perm):
        # Check if user has requested access (based on effective ACL) on the
        # specified resource.
        start_time = time.time()
        request = "%s;%s;%s" % (name, resource, perm)
        try:
            groups = set([])
            try:
                info = IdentityManager.GetIdentityInfoFromDB(name)
                groups = set(map(lambda x: int(x), info["groups"]))
            except Exception as e:
                logger.warning("Failed to get group id list. Ex: %s", e)

            # TODO: handle is_deny
            acl_path = resource
            while acl_path:
                acl = ACLManager.GetResourceAcl(acl_path)

                for ace in acl:
                    ace_id = int(ace["identityId"])
                    in_groups = ace_id in groups
                    in_range = ace_id < INVALID_RANGE_START

                    if ace["identityName"] == name or (in_groups and in_range):
                        if not (perm & (~ace["permissions"])):
                            duration = time.time() - start_time
                            logger.info("Yes for %s in time %s", request,
                                        duration)
                            return True

                acl_path = AuthorizationManager.__get_parent_path(acl_path)

            duration = time.time() - start_time
            logger.info("No for %s in time %s", request, duration)
            return False

        except Exception as e:
            duration = time.time() - start_time
            logger.error("No for %s in time %s. Ex: %s", request, duration, e)
            return False

    @staticmethod
    def HasAccess(name, resource_type, resource_name, perm):
        resource = AuthorizationManager.GetResourceAclPath(
            resource_name, resource_type)
        return AuthorizationManager._has_access(name, resource, perm)

    @staticmethod
    def __get_accessible_acl(name, perm):
        # Return all access control entries (for resources on which user has
        # read access).
        ret = []
        try:
            acl = ACLManager.GetAllAcl()
            for ace in acl:
                res = ace["resource"]
                if AuthorizationManager._has_access(name, res, perm):
                    ret.append(ace)
            return ret
        except Exception as e:
            logger.error("Fail to get ACL for %s;%s, ex: %s", name, perm, e)
        return ret

    @staticmethod
    def GetAcl(name):
        return AuthorizationManager.__get_accessible_acl(name, Permission.User)

    @staticmethod
    def IsClusterAdmin(name):
        return AuthorizationManager._has_access(
            name, AuthorizationManager.CLUSTER_ACL_PATH, Permission.Admin)

    @staticmethod
    def __get_parent_path(acl_path):
        if AuthorizationManager.ACL_DELIMITER in acl_path:
            return acl_path.rsplit(AuthorizationManager.ACL_DELIMITER, 1)[0]
        else:
            return ""

    @staticmethod
    def GetResourceAclPath(resource_identifier, resource_type):
        if resource_type == ResourceType.VC:
            return AuthorizationManager.CLUSTER_ACL_PATH + \
                   AuthorizationManager.ACL_DELIMITER + \
                   ResourceType.reverse_mapping[resource_type] + \
                   AuthorizationManager.TYPE_NAME_DELIMITER + \
                   resource_identifier.strip(AuthorizationManager.ACL_DELIMITER)

        elif resource_type == ResourceType.Cluster:
            return AuthorizationManager.CLUSTER_ACL_PATH


class ACLManager:
    # Add/Update a specific access control entry.
    @staticmethod
    def UpdateAce(name, resource, perm, is_deny):
        ret = False
        data_handler = None
        try:
            data_handler = DataHandler()
            if name.isdigit():
                uid = int(name)
            else:
                info = IdentityManager.GetIdentityInfoFromDB(name)
                uid = info["uid"]
            ret = data_handler.UpdateAce(name, uid, resource, perm, is_deny)

            with acl_cache_lock:
                acl_cache.pop(RESOURCE_KEY_PREFIX + resource, None)
                acl_cache.pop(IDENTITY_KEY_PREFIX + name, None)
        except Exception as e:
            ace = "%s;%s;%s;%s" % (name, resource, perm, is_deny)
            logger.warning("Failed to update ace %s. Ex: %s", ace, e)
        finally:
            if data_handler is not None:
                data_handler.Close()
        return ret

    @staticmethod
    def DeleteAce(name, resource):
        ret = False
        data_handler = None
        try:
            data_handler = DataHandler()
            ret = data_handler.DeleteAce(name, resource)

            with acl_cache_lock:
                acl_cache.pop(RESOURCE_KEY_PREFIX + resource, None)
                acl_cache.pop(IDENTITY_KEY_PREFIX + name, None)

        except Exception as e:
            logger.warning("Fail to delete ace for %s; %s. Ex: %s", name,
                           resource, e)
        finally:
            if data_handler is not None:
                data_handler.Close()
        return ret

    @staticmethod
    def DeleteResourceAcl(resource):
        ret = False
        data_handler = None
        try:
            data_handler = DataHandler()
            ret = data_handler.DeleteResourceAcl(resource)

            with acl_cache_lock:
                res_key = RESOURCE_KEY_PREFIX + resource
                items = acl_cache.pop(res_key, None)
                if items is not None:
                    for ace in items:
                        id_key = IDENTITY_KEY_PREFIX + ace["identityName"]
                        acl_cache.pop(id_key, None)
        except Exception as e:
            logger.error("Failed to delete resource acl for %s. Ex: %s",
                         resource, e)
        finally:
            if data_handler is not None:
                data_handler.Close()
        return ret

    @staticmethod
    def GetAllAcl():
        acl = []
        try:
            with acl_cache_lock:
                for item in acl_cache.keys():
                    if item.startswith(RESOURCE_KEY_PREFIX):
                        acl.extend(acl_cache[item])
        except KeyError:
            pass

        if acl:
            return acl

        data_handler = None
        try:
            data_handler = DataHandler()
            acl = data_handler.GetAcl()

            resources = {}
            identities = {}
            for ace in acl:
                res_key = RESOURCE_KEY_PREFIX + ace["resource"]
                if res_key not in resources:
                    resources[res_key] = []
                resources[res_key].append(ace)

                id_key = IDENTITY_KEY_PREFIX + ace["identityName"]
                if id_key not in identities:
                    identities[id_key] = []
                identities[id_key].append(ace)

            with acl_cache_lock:
                acl_cache.update(resources)
                acl_cache.update(identities)

        except Exception as e:
            logger.warning("Fail to get all ACLs. Ex: %s", e)

        finally:
            if data_handler is not None:
                data_handler.Close()
        return acl

    @staticmethod
    def GetResourceAcl(resource):
        try:
            with acl_cache_lock:
                res_key = RESOURCE_KEY_PREFIX + resource
                return acl_cache[res_key]
        except KeyError:
            pass

        data_handler = None
        ret = []
        try:
            data_handler = DataHandler()
            ret = data_handler.GetResourceAcl(resource)

            identities = {}
            for ace in ret:
                id_key = IDENTITY_KEY_PREFIX + ace["identityName"]
                if id_key not in identities:
                    identities[id_key] = []
                identities[id_key].append(ace)

            with acl_cache_lock:
                res_key = RESOURCE_KEY_PREFIX + resource
                acl_cache[res_key] = ret
                acl_cache.update(identities)
        except Exception as e:
            logger.error("Failed to get resource acl for %s. Ex: %s", resource,
                         e)
        finally:
            if data_handler is not None:
                data_handler.Close()
        return ret

    @staticmethod
    def UpdateAclIdentityId(name, identity_id):
        ret = False
        data_handler = None
        try:
            data_handler = DataHandler()
            ret = data_handler.UpdateAclIdentityId(name, identity_id)

            with acl_cache_lock:
                id_key = IDENTITY_KEY_PREFIX + name
                items = acl_cache.pop(id_key, None)
                if items is not None:
                    for ace in items:
                        res_key = RESOURCE_KEY_PREFIX + ace["resource"]
                        acl_cache.pop(res_key, None)
        except Exception as e:
            logger.error("Failed to update identity ID for %s;%s. Ex: %s", name,
                         identity_id, e)
        finally:
            if data_handler is not None:
                data_handler.Close()
        return ret


class IdentityManager:
    @staticmethod
    @cached(cache=id_cache, key=lambda name: name, lock=id_cache_lock)
    def GetIdentityInfoFromDB(name):
        lst = DataManager.GetIdentityInfo(name)
        if lst:
            return lst[0]
        else:
            logger.warning("Identity name %s not found in DB", name)
            return INVALID_INFO

    @staticmethod
    def UpdateIdentityInfo(name, uid, gid, groups, public_key, private_key):
        ret = False
        data_handler = None
        try:
            data_handler = DataHandler()
            ret = data_handler.UpdateIdentityInfo(name, uid, gid, groups,
                                                  public_key, private_key)
            with id_cache_lock:
                id_cache.pop(name, None)
        except Exception as e:
            logger.exception("Failed to update identity info for %s", name)
        finally:
            if data_handler is not None:
                data_handler.Close()
        return ret
