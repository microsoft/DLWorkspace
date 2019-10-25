from DataHandler import DataHandler, DataManager
import logging
import json
import requests
import random
from config import config
import timeit
from cache import fcache

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


class AuthorizationManager:
    #TODO : Add Cache to aovid frequent DB calls

    CLUSTER_ACL_PATH = "Cluster"
    ACL_DELIMITER = "/"
    TYPE_NAME_DELIMITER = ":"

    # Check if user has requested access (based on effective ACL) on the specified resource.
    # @fcache(TTLInSec=300): TODO rewrite cache
    @staticmethod
    def _HasAccess(identityName, resourceAclPath, permissions):
        start_time = timeit.default_timer()
        requestedAccess = '%s;%s;%s' % (str(identityName), resourceAclPath, str(permissions))

        data_handler = None
        try:           
            identities = []
            identities.extend(IdentityManager.GetIdentityInfoFromDB(identityName)["groups"])

            data_handler = DataHandler()

            #TODO: handle isDeny
            while resourceAclPath:
                #logger.debug('resourceAclPath ' + resourceAclPath)
                acl = data_handler.GetResourceAcl(resourceAclPath)
                for ace in acl:
                    for identity in identities:
                        #logger.debug('identity %s' % identity)
                        if ace["identityName"] == identityName or (str(ace["identityId"]) == str(identity)  and (int(identity) < INVALID_RANGE_START or int(identity) > INVALID_RANGE_END)):
                            permissions = permissions & (~ace["permissions"])
                            if not permissions:
                                logger.info('Yes for %s in time %s' % (requestedAccess, str(timeit.default_timer() - start_time)))
                                return True

                resourceAclPath = AuthorizationManager.__GetParentPath(resourceAclPath)
            logger.info('No for %s in time %s' % (requestedAccess, str(timeit.default_timer() - start_time)))
            return False

        except Exception as e:
            logger.error('Exception: '+ str(e))
            logger.warn('No (exception) for %s in time %s' % (requestedAccess, str(timeit.default_timer() - start_time)))
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
