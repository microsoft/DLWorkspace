from config import config
from cache import fcache

if "datasource" in config and config["datasource"] == "MySQL":
    from MySQLDataHandler import DataHandler
else:
    from SQLDataHandler import DataHandler


class DataManager:
    @staticmethod
    def GetClusterStatus():
        dataHandler = DataHandler()
        ret = None
        try:
            ret = dataHandler.GetClusterStatus()
        finally:
            dataHandler.Close()
        return ret


    @staticmethod
    def ListVCs():
        dataHandler = DataHandler()
        ret = None
        try:
            ret = dataHandler.ListVCs()
        finally:
            dataHandler.Close()
        return ret

    
    @staticmethod
    def GetResourceAcl(resourceAclPath):
        dataHandler = DataHandler()
        ret = None
        try:
            ret = dataHandler.GetResourceAcl(resourceAclPath)
        finally:
            dataHandler.Close()
        return ret


    @staticmethod
    def GetIdentityInfo(identityName):
        dataHandler = DataHandler()
        ret = None
        try:
            ret = dataHandler.GetIdentityInfo(identityName)
        finally:
            dataHandler.Close()
        return ret


    @staticmethod
    def GetAllPendingJobs(vcName):
        dataHandler = DataHandler()
        ret = None
        try:
            ret = dataHandler.GetJobList("all",vcName,None, "running,queued,scheduling,unapproved,pausing,paused", ("=","or"))
        finally:
            dataHandler.Close()
        return ret
    

    @staticmethod
    def GetTemplates(scope):
        dataHandler = DataHandler()
        ret = []
        try:
            ret = dataHandler.GetTemplates(scope)
        finally:
            dataHandler.Close()
        return ret

    @staticmethod
    def UpdateTemplate(name, scope, json):
        dataHandler = DataHandler()
        ret = None
        try:
            ret = dataHandler.UpdateTemplate(name, scope, json)
        finally:
            dataHandler.Close()
        return ret

    @staticmethod
    def DeleteTemplate(name, scope):
        dataHandler = DataHandler()
        ret = None
        try:
            ret = dataHandler.DeleteTemplate(name, scope)
        finally:
            dataHandler.Close()
        return ret
