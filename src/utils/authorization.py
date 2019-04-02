from DataHandler import DataHandler
from MyLogger import MyLogger
import json
import requests

logger = MyLogger()

def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    reverse = dict((value, key) for key, value in enums.items())
    enums['reverse_mapping'] = reverse
    return type('Enum', (), enums)

Permission = enum(Unauthorized=0, User=1, Collaborator=3, Admin=7)
ResourceType = enum(Cluster=1, VC=2, Job=3)
'''

import enum
class Permission(enum.Enum):
    Unauthorized = 0
    User = 1
    Collaborator=3
    Admin = 7


class ResourceType(enum.Enum):
    Cluster = 1
    NFS = 2
    VC = 3
    Job = 4
    Template = 5
'''


class AuthorizationManager:
    #TODO : Add Cache to aovid frequent DB calls

    CLUSTER_ACL_PATH = "Cluster"
    ACL_DELIMITER = "/"
    TYPE_NAME_DELIMITER = ":"
    WinBindUrl = "http://onenet40.redmond.corp.microsoft.com/domaininfo/GetUserId?userName={0}" #TODO:read form config

    # Check if user has requested access (based on effective ACL) on the specified resource.
    @staticmethod
    def _HasAccess(identityName, resourceAclPath, permissions):
        dataHandler = DataHandler() 
        try:
            logger.info('HasAccess invoked!')             
            identities = []
            identities.append(IdentityManager(AuthorizationManager.WinBindUrl).GetIdentityInfo(identityName)["groups"])

            logger.info('initial resourceAclPath ' + resourceAclPath)
            #TODO: handle isDeny
            while resourceAclPath:
                logger.info('resourceAclPath ' + resourceAclPath)
                acl = dataHandler.GetResourceAcl(resourceAclPath)
                for ace in acl:
                    for identity in identities:
                        if ace["identityId"] == identity or ace["identityName"] == identityName:
                            permissions = permissions & (~ace["permissions"])
                            if not permissions:
                                logger.info('access : Yes')
                                return True

                resourceAclPath = AuthorizationManager.__GetParentPath(resourceAclPath)
            logger.info('access : No')
            return False

        except Exception as e:
            logger.error('Exception: '+ str(e))
            logger.warn("HasAccess failed for user %s" % identityName)
            logger.info('access : No (exception)')
            return False

        finally:
            dataHandler.Close()


    @staticmethod
    def HasAccess(identityName, resourceType, resourceName, permissions):
        resourceAclPath = AuthorizationManager.GetResourceAclPath(resourceName, resourceType)
        return AuthorizationManager._HasAccess(identityName, resourceAclPath, permissions)


    # Add/Update a specific access control entry. 
    @staticmethod
    def UpdateAce(identityName, resourceAclPath, permissions, isDeny):
        dataHandler = DataHandler() 
        try:                  
            identityId = IdentityManager(AuthorizationManager.WinBindUrl).GetIdentityInfo(identityName)["uid"]
            if identityId == -1:
                identityId = 0
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
                if AuthorizationManager.HasAccess(userName, ace["resource"], permissions): #resource
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
        return AuthorizationManager.HasAccess(userName, AuthorizationManager.CLUSTER_ACL_PATH, Permission.Admin)


    @staticmethod
    def __GetParentPath(aclPath):
        if AuthorizationManager.ACL_DELIMITER in aclPath:
            return aclPath.rsplit(AuthorizationManager.ACL_DELIMITER, 1)[0]
        else:
            return ""


    @staticmethod
    def GetResourceAclPath(resourceIdentifier, resourceType):
        if (resourceType == ResourceType.VC):
            #return AuthorizationManager.CLUSTER_ACL_PATH + AuthorizationManager.ACL_DELIMITER + ResourceType(resourceType).name + AuthorizationManager.TYPE_NAME_DELIMITER + resourceIdentifier.strip(AuthorizationManager.ACL_DELIMITER)
            return AuthorizationManager.CLUSTER_ACL_PATH + AuthorizationManager.ACL_DELIMITER + ResourceType.reverse_mapping[resourceType] + AuthorizationManager.TYPE_NAME_DELIMITER + resourceIdentifier.strip(AuthorizationManager.ACL_DELIMITER)
        elif resourceType == ResourceType.Cluster:
            return AuthorizationManager.CLUSTER_ACL_PATH



class IdentityManager:
    serverUrl = ""
    #TODO: do we need to cache?

    def __init__(self, winbindServerUrl):
        self.serverUrl = winbindServerUrl
    

    def GetIdentityInfo(self, identityName):
        dataHandler = DataHandler()
        try:           
            # winbind (depending on configs) handles nested groups for userIds
            response = requests.get(self.serverUrl.format(identityName))
            info = json.loads(response.text)

            dataHandler.UpdateIdentityInfo(identityName, info["uid"], info["groups"])

            return info
        except Exception as e:
            logger.error('Exception: '+ str(e))
            logger.warn("GetIdentityInfo from winbind failed for identity %s" % identityName)

            info = {}
            info["uid"] = -1
            info["gid"] = -1
            info["groups"] = [-1]

            lst = dataHandler.GetIdentityInfo(identityName)
            if lst:
                info["uid"] = lst[0][1]
                info["gid"] = lst[0][1]
                info["groups"] = lst[0][2]
            else:
                logger.warn("GetIdentityInfo : Identity %s not found in DB" % identityName)
            return info

        finally:
            dataHandler.Close()