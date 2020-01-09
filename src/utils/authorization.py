from DataHandler import DataHandler, DataManager
import logging
import json
import requests
import random
from config import config
import time
import threading
from cachetools import cached, TTLCache

logger = logging.getLogger(__name__)

def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    reverse = dict((value, key) for key, value in enums.items())
    enums['reverse_mapping'] = reverse
    return type('Enum', (), enums)

Permission = enum(Unauthorized=0, User=1, Collaborator=3, Admin=7)
ResourceType = enum(Cluster=1, VC=2, Job=3)

INVALID_RANGE_START = 900000000
INVALID_RANGE_END = 999999998
INVALID_ID = 999999999

INVALID_INFO = {
    "uid": INVALID_ID,
    "gid": INVALID_ID,
    "groups": [INVALID_ID]
}


DEFAULT_EXPIRATION = 30 * 60
acl_cache = TTLCache(maxsize=10240, ttl=DEFAULT_EXPIRATION)
acl_cache_lock = threading.Lock()
resourceKeyPrefix = "r/"
identityKeyPrefix = "i/"
identity_cache = TTLCache(maxsize=10240, ttl=DEFAULT_EXPIRATION)
identity_cache_lock = threading.Lock()

class AuthorizationManager:

    CLUSTER_ACL_PATH = "Cluster"
    ACL_DELIMITER = "/"
    TYPE_NAME_DELIMITER = ":"

    # Check if user has requested access (based on effective ACL) on the specified resource.
    @staticmethod
    def _HasAccess(identity_name, resource_acl_path, permissions):
        start_time = time.time()
        requested_access = "%s;%s;%s" % (str(identity_name), resource_acl_path, str(permissions))
        try:
            identities = set([])
            try:
                identities = IdentityManager.GetIdentityInfoFromDB(identity_name)["groups"]
                identities = set(map(lambda x: int(x), identities))
            except Exception as e:
                logger.warn("Failed to get identities list: %s" % e)

            #TODO: handle isDeny
            while resource_acl_path:
                acl = ACLManager.GetResourceAcl(resource_acl_path)

                for ace in acl:
                    ace_id = int(ace["identityId"])
                    id_in_identities = ace_id in identities
                    id_in_range = ace_id < INVALID_RANGE_START or ace_id > INVALID_RANGE_END
                    if ace["identityName"] == identity_name or (id_in_identities and id_in_range):
                        permission = permissions & (~ace["permissions"])
                        if not permission:
                            logger.info('Yes for %s in time %f' % (requested_access, time.time() - start_time))
                            return True

                resource_acl_path = AuthorizationManager.__GetParentPath(resource_acl_path)

            logger.info("No for %s in time %s" % (requested_access, time.time() - start_time))
            return False

        except Exception as e:
            logger.error("No (exception) for %s in time %f, ex: %s", requested_access, time.time() - start_time, str(e))
            return False


    @staticmethod
    def HasAccess(identityName, resourceType, resourceName, permissions):
        resourceAclPath = AuthorizationManager.GetResourceAclPath(resourceName, resourceType)
        return AuthorizationManager._HasAccess(identityName, resourceAclPath, permissions)


    # Return all access control entries (for resources on which user has read access).
    @staticmethod
    def __GetAccessibleAcl(userName, permissions):
        ret = []
        try:
            acl = ACLManager.GetAllAcl()
            for ace in acl:
                if AuthorizationManager._HasAccess(userName, ace["resource"], permissions): #resource
                    ret.append(ace)

            return ret

        except Exception as e:
            logger.error("Fail to get ACL for user %s, ex: %s", userName, str(e))
        return ret

    @staticmethod
    def GetAcl(username):
        return AuthorizationManager.__GetAccessibleAcl(username, Permission.User)

    @staticmethod
    def IsClusterAdmin(userName):
        return AuthorizationManager._HasAccess(userName, AuthorizationManager.CLUSTER_ACL_PATH, Permission.Admin)


    @staticmethod
    def __GetParentPath(aclPath):
        if AuthorizationManager.ACL_DELIMITER in aclPath:
            return aclPath.rsplit(AuthorizationManager.ACL_DELIMITER, 1)[0]
        else:
            return ""

    @staticmethod
    def GetResourceAclPath(resourceIdentifier, resourceType):
        if (resourceType == ResourceType.VC):
            return AuthorizationManager.CLUSTER_ACL_PATH + AuthorizationManager.ACL_DELIMITER + ResourceType.reverse_mapping[resourceType] + AuthorizationManager.TYPE_NAME_DELIMITER + resourceIdentifier.strip(AuthorizationManager.ACL_DELIMITER)
        elif resourceType == ResourceType.Cluster:
            return AuthorizationManager.CLUSTER_ACL_PATH


class ACLManager:
    # Add/Update a specific access control entry. 
    @staticmethod
    def UpdateAce(identityName, resource, permissions, isDeny):
        dataHandler = DataHandler()
        ret = False
        try:
            identityId = 0
            if identityName.isdigit():
                identityId = int(identityName)
            else:               
                identityId = IdentityManager.GetIdentityInfoFromDB(identityName)["uid"]
                if identityId == INVALID_ID:
                    info = IdentityManager.GetIdentityInfoFromAD(identityName)
                    IdentityManager.UpdateIdentityInfo(identityName, info["uid"], info["gid"], info["groups"])
                    identityId = info["uid"]
            ret = dataHandler.UpdateAce(identityName, identityId, resource, permissions, isDeny)

            with acl_cache_lock:
                acl_cache.pop(resourceKeyPrefix + resource, None)
                acl_cache.pop(identityKeyPrefix + identityName, None)
        except Exception as e:
            logger.warn("Fail to Update Ace for user %s, ex: %s" , identityName, str(e))
        finally:
            dataHandler.Close()
        return ret

    @staticmethod
    def DeleteAce(identityName, resource):
        dataHandler = DataHandler()
        ret = False
        try:                  
            ret = dataHandler.DeleteAce(identityName, resource)

            with acl_cache_lock:
                acl_cache.pop(resourceKeyPrefix + resource, None)
                acl_cache.pop(identityKeyPrefix + identityName, None)

        except Exception as e:
            logger.warn("Fail to Delete Ace for user %s, ex: %s" , identityName, str(e))
        finally:
            dataHandler.Close()
        return ret

    @staticmethod
    def DeleteResourceAcl(resource):
        dataHandler = DataHandler()
        ret = False
        try:           
            ret = dataHandler.DeleteResourceAcl(resource)

            with acl_cache_lock:
                items = acl_cache.pop(resourceKeyPrefix + resource, None)
                if items is not None:
                    for ace in items:
                        acl_cache.pop(identityKeyPrefix + ace["identityName"], None)
        except Exception as e:
            logger.error("DeleteResourceAcl failed for %s, ex: %s" , resourceAclPath, str(e))
        finally:
            dataHandler.Close()
        return ret

    @staticmethod
    def GetAllAcl():
        acl = []
        try:
            with acl_cache_lock:
                for item in acl_cache.keys():
                    if item.startswith(resourceKeyPrefix):
                        acl.extend(acl_cache[item])
        except KeyError:
            pass

        if acl:
            return acl

        dataHandler = DataHandler()
        try:           
            acl = dataHandler.GetAcl()

            resources = {}
            identities = {}
            for ace in acl:
                resourceKey = resourceKeyPrefix + ace["resource"]
                if resourceKey not in resources:
                    resources[resourceKey] = []
                resources[resourceKey].append(ace)

                identityKey = identityKeyPrefix + ace["identityName"]
                if identityKey not in identities:
                    identities[identityKey] = []
                identities[identityKey].append(ace)

            with acl_cache_lock:
                acl_cache.update((resources))
                acl_cache.update((identities))

        except Exception as e:
            logger.warn("Fail to get ACL for user %s, ex: %s" , userName, str(e))

        finally:
            dataHandler.Close()
        return acl

    @staticmethod
    def GetResourceAcl(resource):
        try:
            with acl_cache_lock:
                return acl_cache[resourceKeyPrefix + resource]
        except KeyError:
            pass

        dataHandler = DataHandler()
        ret = []
        try:
            ret = dataHandler.GetResourceAcl(resource)

            identities = {}
            for ace in ret:
                identityKey = identityKeyPrefix + ace["identityName"]
                if identityKey not in identities:
                    identities[identityKey] = []
                identities[identityKey].append(ace)

            with acl_cache_lock:
                acl_cache[resourceKeyPrefix + resource] = ret
                acl_cache.update((identities))
        except Exception as e:
            logger.error("Get resoure acl error for resource: %s, ex: %s", resource, str(e))
        finally:
            dataHandler.Close()
        return ret

    @staticmethod
    def UpdateAclIdentityId(identityName, identityId):
        dataHandler = DataHandler()
        ret = False
        try:
            ret = dataHandler.UpdateAclIdentityId(identityName, identityId)

            with acl_cache_lock:
                items = acl_cache.pop(identityKeyPrefix + identityName, None)
                if items is not None:
                    for ace in items:
                        acl_cache.pop(resourceKeyPrefix + ace["resource"], None)
        except Exception as e:
            logger.error("UpdateAclIdentityId failed for %s, ex: %s" , resourceAclPath, str(e))
        finally:
            dataHandler.Close()
        return ret


class IdentityManager:


    @staticmethod
    def GetIdentityInfoFromAD(identityName):
        winBindConfigured = False

        if "WinbindServers" in config:
            if not config["WinbindServers"] and len(config["WinbindServers"]) > 0:
                if not config["WinbindServers"][0]:
                    try:
                        winBindConfigured = True
                        logger.info('Getting Identity Info From AD...')
                        # winbind (depending on configs) handles nested groups for userIds
                        response = requests.get(config["WinbindServers"][0].format(identityName))                       
                        info = json.loads(response.text)
                        return info
                    except Exception as ex:
                        logger.error('Exception: '+ str(ex))
                        raise ex
        if not winBindConfigured:
            randomId = random.randrange(INVALID_RANGE_START, INVALID_RANGE_END)
            info = {}
            info["uid"] = randomId
            info["gid"] = randomId
            info["groups"] = [randomId]

            return info

    @staticmethod
    @cached(cache=identity_cache, key=lambda identityName: identityName, lock=identity_cache_lock)
    def GetIdentityInfoFromDB(identityName):
        lst = DataManager.GetIdentityInfo(identityName)
        if lst:
            return lst[0]
        else:
            logger.warn("GetIdentityInfo : Identity %s not found in DB" % identityName)
            info = {}
            info["uid"] = INVALID_ID
            info["gid"] = INVALID_ID
            info["groups"] = [INVALID_ID]
            return info

    @staticmethod
    def UpdateIdentityInfo(identityName, uid, gid, groups):
        dataHandler = DataHandler()
        ret = False
        try:
            ret = dataHandler.UpdateIdentityInfo(identityName, uid, gid, groups)
            with identity_cache_lock:
                identity_cache.pop(identityName, None)
        except Exception as e:
                logger.error("update identity info error for identity: %s, ex: %s", identityName, str(e))
        finally:
            dataHandler.Close()
        return ret