from DataHandler import DataHandler, DataManager
import logging
import json
import requests
import random
from config import config
import time
import threading

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


DEFAULT_EXPIRATION = 5 * 60


class SimpleCache(object):
    def __init__(self, expiration=DEFAULT_EXPIRATION):
        self.expiration = expiration
        self.lock = threading.Lock()
        self.cache = dict()

    def get(self, key):
        with self.lock:
            if key in self.cache:
                value, timestamp = self.cache[key]
                if time.time() - timestamp <= self.expiration:
                    return value
            return None

    def add(self, key, value):
        with self.lock:
            self.cache[key] = (value, time.time())


resource_acl_cache = SimpleCache()


def get_identity_info_from_db(data_handler, identity_name):
    try:
        info_list = data_handler.GetIdentityInfo(identity_name)
        if len(info_list) > 0:
            return info_list[0]
        else:
            logger.warn("Identity name %s not found in DB" % identity_name)
            return INVALID_INFO
    except Exception as e:
        logger.error("Failed to get identity info for %s from DB: %s" % (identity_name, e))

    return INVALID_INFO


class AuthorizationManager:
    #TODO : Add Cache to aovid frequent DB calls

    CLUSTER_ACL_PATH = "Cluster"
    ACL_DELIMITER = "/"
    TYPE_NAME_DELIMITER = ":"

    # Check if user has requested access (based on effective ACL) on the specified resource.
    @staticmethod
    def _HasAccess(identity_name, resource_acl_path, permissions):
        start_time = time.time()
        requested_access = "%s;%s;%s" % (str(identity_name), resource_acl_path, str(permissions))

        value = resource_acl_cache.get(requested_access)
        if value is not None:
            logger.info('[cached] Yes for %s in time %s' % (requested_access, time.time() - start_time))
            return value

        data_handler = None
        try:
            data_handler = DataHandler()

            identities = []
            try:
                identities = get_identity_info_from_db(data_handler, identity_name)["groups"]
                identities = map(lambda x: int(x), identities)
            except Exception as e:
                logger.warn("Failed to get identities list: %s" % e)
                identities = []

            #TODO: handle isDeny
            while resource_acl_path:
                acl = data_handler.GetResourceAcl(resource_acl_path)

                for ace in acl:
                    ace_id = int(ace["identityId"])
                    id_in_identities = ace_id in identities
                    id_in_range = ace_id < INVALID_RANGE_START or ace_id > INVALID_RANGE_END
                    if ace["identityName"] == identity_name or (id_in_identities and id_in_range):
                        permissions = permissions & (~ace["permissions"])
                        if not permissions:
                            logger.info('Yes for %s in time %s' % (requested_access, time.time() - start_time))
                            resource_acl_cache.add(requested_access, True)
                            return True

                resource_acl_path = AuthorizationManager.__GetParentPath(resource_acl_path)

            logger.info("No for %s in time %s" % (requested_access, time.time() - start_time))
            resource_acl_cache.add(requested_access, False)
            return False

        except Exception as e:
            logger.error("Exception: %s" % e)
            logger.warn("No (exception) for %s in time %s" % (requested_access, time.time() - start_time))
            return False

        finally:
            if data_handler is not None:
                data_handler.Close()


    @staticmethod
    def HasAccess(identityName, resourceType, resourceName, permissions):
        resourceAclPath = AuthorizationManager.GetResourceAclPath(resourceName, resourceType)
        return AuthorizationManager._HasAccess(identityName, resourceAclPath, permissions)


    # Add/Update a specific access control entry. 
    @staticmethod
    def UpdateAce(identityName, resourceAclPath, permissions, isDeny):
        dataHandler = DataHandler() 
        try:
            identityId = 0
            if identityName.isdigit():
                identityId = int(identityName)
            else:               
                identityId = IdentityManager.GetIdentityInfoFromDB(identityName)["uid"]
                if identityId == INVALID_ID:
                    info = IdentityManager.GetIdentityInfoFromAD(identityName)
                    dataHandler.UpdateIdentityInfo(identityName, info["uid"], info["gid"], info["groups"])
                    identityId = info["uid"]
            return dataHandler.UpdateAce(identityName, identityId, resourceAclPath, permissions, isDeny)

        except Exception as e:
            logger.error('Exception: '+ str(e))
            logger.warn("Fail to Update Ace for user %s" % identityName)
            return False

        finally:
            dataHandler.Close()


    @staticmethod
    def DeleteAce(identityName, resourceAclPath):
        dataHandler = DataHandler() 
        try:                  
            return dataHandler.DeleteAce(identityName, resourceAclPath)

        except Exception as e:
            logger.error('Exception: '+ str(e))
            logger.warn("Fail to Delete Ace for user %s" % identityName)
            return False

        finally:
            dataHandler.Close()


    @staticmethod
    def DeleteResourceAcl(resourceAclPath):
        dataHandler = DataHandler()
        try:           
            return dataHandler.DeleteResourceAcl(resourceAclPath)    

        except Exception as e:
            logger.error('Exception: '+ str(e))
            logger.warn("DeleteResourceAcl failed for %s" % resourceAclPath)
            return False

        finally:
            dataHandler.Close()


    # Return all access control entries (for resources on which user has read access).
    @staticmethod
    def __GetAccessibleAcl(userName, permissions):
        dataHandler = DataHandler()
        try:           
            acl = dataHandler.GetAcl()
            ret = []

            for ace in acl:
                if AuthorizationManager._HasAccess(userName, ace["resource"], permissions): #resource
                    ret.append(ace)

            return ret

        except Exception as e:
            logger.error('Exception: '+ str(e))
            logger.warn("Fail to get ACL for user %s, return empty list" % userName)
            return []

        finally:
            dataHandler.Close()


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
