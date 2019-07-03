# from config import config
import mysql.connector
import json
import base64
import os

import timeit

from Queue import Queue

from config import config
from config import global_vars
from MyLogger import MyLogger

logger = MyLogger()


class DataHandler:


    def __init__(self):
        start_time = timeit.default_timer()
        self.database = "DLWSCluster-%s" % config["clusterId"]
        self.jobtablename = "jobs"
        self.identitytablename = "identity"
        self.acltablename = "acl"
        self.vctablename = "vc"
        self.storagetablename = "storage"
        self.clusterstatustablename = "clusterstatus"
        self.commandtablename = "commands"
        server = config["mysql"]["hostname"]
        username = config["mysql"]["username"]
        password = config["mysql"]["password"]


        self.conn = mysql.connector.connect(user=username, password=password,
                                            host=server, database=self.database)

        self.CreateDatabase()
        self.CreateTable()


        elapsed = timeit.default_timer() - start_time
        logger.info("DataHandler initialization, time elapsed %f s" % elapsed)



    def CreateDatabase(self):
        if "initSQLDB" not in global_vars or not global_vars["initSQLDB"]:
            logger.info("===========init SQL database===============")
            global_vars["initSQLDB"] = True

            server = config["mysql"]["hostname"]
            username = config["mysql"]["username"]
            password = config["mysql"]["password"]

            conn = mysql.connector.connect(user=username, password=password,
                                          host=server)
            sql = " CREATE DATABASE IF NOT EXISTS `%s` DEFAULT CHARACTER SET 'utf8' " % (self.database)
            cursor = conn.cursor()
            cursor.execute(sql)
            conn.commit()
            cursor.close()
            conn.close()

    def CreateTable(self):
        if "initSQLTable" not in global_vars or not global_vars["initSQLTable"]:
            logger.info("===========init SQL Tables ===============")
            global_vars["initSQLTable"] = True
            sql = """
                CREATE TABLE IF NOT EXISTS `%s`
                (
                    `id`        INT          NOT NULL AUTO_INCREMENT,
                    `jobId` varchar(50)   NOT NULL,
                    `familyToken` varchar(50)   NOT NULL,
                    `isParent` INT   NOT NULL,
                    `jobName`         varchar(1024) NOT NULL,
                    `userName`         varchar(255) NOT NULL,
                    `vcName`         varchar(255) NOT NULL,
                    `jobStatus`         varchar(255) NOT NULL DEFAULT 'unapproved',
                    `jobStatusDetail` LONGTEXT  NULL,
                    `jobType`         varchar(255) NOT NULL,
                    `jobDescriptionPath`  TEXT NULL,
                    `jobDescription`  LONGTEXT  NULL,
                    `jobTime` DATETIME     DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    `endpoints` LONGTEXT  NULL,
                    `errorMsg` LONGTEXT  NULL,
                    `jobParams` LONGTEXT  NOT NULL,
                    `jobMeta` LONGTEXT  NULL,
                    `jobLog` LONGTEXT  NULL,
                    `retries`             int    NULL DEFAULT 0,
                    `lastUpdated` DATETIME     DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    PRIMARY KEY (`id`),
                    UNIQUE(`jobId`),
                    INDEX (`userName`),
                    INDEX (`jobTime`),
                    INDEX (`jobId`),
                    INDEX (`jobStatus`)
                );
                """ % (self.jobtablename)

            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()

            sql = """
                CREATE TABLE IF NOT EXISTS `%s`
                (
                    `id`        INT   NOT NULL AUTO_INCREMENT,
                    `status`         LONGTEXT NOT NULL,
                    `time` DATETIME     DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    PRIMARY KEY (`id`)
                )
                """ % (self.clusterstatustablename)

            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()

            sql = """
                CREATE TABLE IF NOT EXISTS `%s`
                (
                    `id`        INT     NOT NULL AUTO_INCREMENT,
                    `jobId` varchar(50)   NOT NULL,
                    `status`         varchar(255) NOT NULL DEFAULT 'pending',
                    `time` DATETIME     DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    `command` TEXT NOT NULL,
                    `output` TEXT NULL,
                    PRIMARY KEY (`id`)
                )
                """ % (self.commandtablename)

            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()

            sql = """
                CREATE TABLE IF NOT EXISTS  `%s`
                (
                    `id`               INT     NOT NULL AUTO_INCREMENT,
                    `storageType`      varchar(255) NOT NULL,
                    `url`              varchar(255) NOT NULL,
                    `metadata`         TEXT NOT NULL,
                    `vcName`           varchar(255) NOT NULL,
                    `defaultMountPath` varchar(255) NOT NULL,
                    `time`             DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    PRIMARY KEY (`id`),
                    CONSTRAINT vc_url UNIQUE(`vcName`,`url`),
                    CONSTRAINT vc_mountPath UNIQUE(`vcName`,`defaultMountPath`)
                )
                """ % (self.storagetablename)

            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()


            sql = """
                CREATE TABLE IF NOT EXISTS  `%s`
                (
                    `id`        INT     NOT NULL AUTO_INCREMENT,
                    `vcName`    varchar(255) NOT NULL UNIQUE,
                    `parent`    varchar(255) DEFAULT NULL,
                    `quota`     varchar(255) NOT NULL,
                    `metadata`  TEXT NOT NULL,
                    `time`      DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    PRIMARY KEY (`id`),
                    CONSTRAINT `hierarchy` FOREIGN KEY (`parent`) REFERENCES `%s` (`vcName`)
                )
                """ % (self.vctablename, self.vctablename)

            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()


            sql = """
                CREATE TABLE IF NOT EXISTS  `%s`
                (
                    `id`            INT     NOT NULL AUTO_INCREMENT,
                    `identityName`  varchar(255) NOT NULL UNIQUE,
                    `uid`           INT NOT NULL,
                    `gid`           INT NOT NULL,
                    `groups`        MEDIUMTEXT NOT NULL,
                    `time`          DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    PRIMARY KEY (`id`)
                )
                """ % (self.identitytablename)

            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()


            sql = """
                CREATE TABLE IF NOT EXISTS  `%s`
                (
                    `id`             INT     NOT NULL AUTO_INCREMENT,
                    `identityName`   varchar(255) NOT NULL,
                    `identityId`     INT NOT NULL,
                    `resource`       varchar(255) NOT NULL,
                    `permissions`    INT NOT NULL,
                    `isDeny`         INT NOT NULL,
                    `time`           DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    PRIMARY KEY (`id`),
                    CONSTRAINT identityName_resource UNIQUE(`identityName`,`resource`)
                )
                """ % (self.acltablename)

            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()


    def AddStorage(self, vcName, url, storageType, metadata, defaultMountPath):
        try:
            start_time = timeit.default_timer()
            sql = "INSERT INTO `"+self.storagetablename+"` (storageType, url, metadata, vcName, defaultMountPath) VALUES (%s,%s,%s,%s,%s)"
            cursor = self.conn.cursor()
            cursor.execute(sql, (storageType, url, metadata, vcName, defaultMountPath))
            self.conn.commit()
            cursor.close()
            elapsed = timeit.default_timer() - start_time
            logger.info ("DataHandler: AddStorage to DB: url : %s, vcName: %s , time elapsed %f s" % (url, vcName, elapsed))
            return True
        except Exception as e:
            logger.error('Exception: '+ str(e))
            return False


    def DeleteStorage(self, vcName, url):
        try:
            start_time = timeit.default_timer()
            sql = "DELETE FROM `%s` WHERE url = '%s' and vcName = '%s'" % (self.storagetablename, url, vcName)
            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()
            elapsed = timeit.default_timer() - start_time
            logger.info ("DataHandler: DeleteStorage: url:%s, vcName:%s, time elapsed %f s" % (url, vcName, elapsed))
            return True
        except Exception as e:
            logger.error('Exception: '+ str(e))
            return False


    def ListStorages(self, vcName):
        start_time = timeit.default_timer()
        cursor = self.conn.cursor()
        query = "SELECT `storageType`,`url`,`metadata`,`vcName`,`defaultMountPath` FROM `%s` WHERE vcName = '%s' " % (self.storagetablename, vcName)
        ret = []
        try:
            cursor.execute(query)
            for (storageType,url,metadata,vcName,defaultMountPath) in cursor:
                record = {}
                record["vcName"] = vcName
                record["url"] = url
                record["storageType"] = storageType
                record["metadata"] = metadata
                record["defaultMountPath"] = defaultMountPath
                ret.append(record)
        except Exception as e:
            logger.error('Exception: '+ str(e))
            pass
        self.conn.commit()
        cursor.close()
        elapsed = timeit.default_timer() - start_time
        logger.info ("DataHandler: ListStorages time elapsed %f s" % (elapsed))
        return ret


    def UpdateStorage(self, vcName, url, storageType, metadata, defaultMountPath):
        try:
            start_time = timeit.default_timer()
            sql = """update `%s` set storageType = '%s', metadata = '%s', defaultMountPath = '%s' where vcName = '%s' and url = '%s' """ % (self.storagetablename, storageType, metadata, defaultMountPath, vcName, url)
            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()
            elapsed = timeit.default_timer() - start_time
            logger.info ("DataHandler: UpdateStorage: vcName: %s, url: %s, time elapsed %f s" % (vcName, url, elapsed))
            return True
        except Exception as e:
            logger.error('Exception: '+ str(e))
            return False


    def AddVC(self, vcName, quota, metadata):
        try:
            start_time = timeit.default_timer()
            sql = "INSERT INTO `"+self.vctablename+"` (vcName, quota, metadata) VALUES (%s,%s,%s)"
            cursor = self.conn.cursor()
            cursor.execute(sql, (vcName, quota, metadata))
            self.conn.commit()
            cursor.close()
            elapsed = timeit.default_timer() - start_time
            logger.info ("DataHandler: AddVC to DB: vcName: %s , time elapsed %f s" % (vcName, elapsed))
            return True
        except Exception as e:
            logger.error('Exception: '+ str(e))
            return False


    def ListVCs(self):
        start_time = timeit.default_timer()
        cursor = self.conn.cursor()
        query = "SELECT `vcName`,`quota`,`metadata` FROM `%s`" % (self.vctablename)
        ret = []
        try:
            cursor.execute(query)
            for (vcName,quota,metadata) in cursor:
                record = {}
                record["vcName"] = vcName
                record["quota"] = quota
                record["metadata"] = metadata
                ret.append(record)
        except Exception as e:
            logger.error('Exception: '+ str(e))
            pass
        self.conn.commit()
        cursor.close()
        elapsed = timeit.default_timer() - start_time
        logger.info ("DataHandler: ListVCs time elapsed %f s" % (elapsed))
        return ret


    def DeleteVC(self, vcName):
        try:
            start_time = timeit.default_timer()
            sql = "DELETE FROM `%s` WHERE vcName = '%s'" % (self.vctablename, vcName)
            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()
            elapsed = timeit.default_timer() - start_time
            logger.info ("DataHandler: DeleteVC: vcName: %s , time elapsed %f s" % (vcName, elapsed))
            return True
        except Exception as e:
            logger.error('Exception: '+ str(e))
            return False


    def UpdateVC(self, vcName, quota, metadata):
        try:
            start_time = timeit.default_timer()
            sql = """update `%s` set quota = '%s', metadata = '%s' where vcName = '%s' """ % (self.vctablename, quota, metadata, vcName)
            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()
            elapsed = timeit.default_timer() - start_time
            logger.info ("DataHandler: UpdateVC: vcName: %s , time elapsed %f s" % (vcName, elapsed))
            return True
        except Exception as e:
            logger.error('Exception: '+ str(e))
            return False


    def GetIdentityInfo(self, identityName):
        start_time = timeit.default_timer()
        cursor = self.conn.cursor()
        query = "SELECT `identityName`,`uid`,`gid`,`groups` FROM `%s` where `identityName` = '%s'" % (self.identitytablename, identityName)
        ret = []
        try:
            cursor.execute(query)
            for (identityName,uid,gid,groups) in cursor:
                record = {}
                record["identityName"] = identityName
                record["uid"] = uid
                record["gid"] = gid
                record["groups"] = json.loads(groups)
                ret.append(record)
        except Exception as e:
            logger.error('GetIdentityInfo Exception: '+ str(e))
            pass
        self.conn.commit()
        cursor.close()
        elapsed = timeit.default_timer() - start_time
        logger.info ("DataHandler: GetIdentityInfo time elapsed %f s" % (elapsed))
        return ret


    def UpdateIdentityInfo(self, identityName, uid, gid, groups):
        try:
            start_time = timeit.default_timer()
            cursor = self.conn.cursor()

            if (isinstance(groups, list)):
                groups = json.dumps(groups)
            
            if len(self.GetIdentityInfo(identityName)) == 0:
                sql = "INSERT INTO `"+self.identitytablename+"` (identityName,uid,gid,groups) VALUES (%s,%s,%s,%s)"
                cursor.execute(sql, (identityName, uid, gid, groups))
            else:
                sql = """update `%s` set uid = '%s', gid = '%s', groups = '%s' where `identityName` = '%s' """ % (self.identitytablename, uid, gid, groups, identityName)
                cursor.execute(sql)

            self.conn.commit()
            cursor.close()
            elapsed = timeit.default_timer() - start_time
            logger.info ("DataHandler: UpdateIdentityInfo %s to database , time elapsed %f s" % (identityName, elapsed))
            return True
        except Exception as e:
            logger.error('UpdateIdentityInfo Exception: '+ str(e))
            return False


    def GetAceCount(self, identityName, resource):
        start_time = timeit.default_timer()
        cursor = self.conn.cursor()
        query = "SELECT count(ALL id) as c FROM `%s` where `identityName` = '%s' and `resource` = '%s'" % (self.acltablename,identityName, resource)
        cursor.execute(query)
        ret = 0
        for c in cursor:
            ret = c[0]
        self.conn.commit()
        cursor.close()
        elapsed = timeit.default_timer() - start_time
        logger.info ("DataHandler: GetAceCount time elapsed %f s" % ( elapsed))
        return ret


    def UpdateAce(self, identityName, identityId, resource, permissions, isDeny):
        try:
            start_time = timeit.default_timer()
            cursor = self.conn.cursor()
            existingAceCount = self.GetAceCount(identityName, resource)
            logger.info(existingAceCount)

            if existingAceCount == 0:
                sql = "INSERT INTO `"+self.acltablename+"` (identityName,identityId,resource,permissions,isDeny) VALUES (%s,%s,%s,%s,%s)"
                cursor.execute(sql, (identityName, identityId, resource, permissions, isDeny))
            else:
                sql = """update `%s` set permissions = '%s' where `identityName` = '%s' and `resource` = '%s' """ % (self.acltablename, permissions, identityName, resource)
                cursor.execute(sql)

            self.conn.commit()
            cursor.close()
            elapsed = timeit.default_timer() - start_time
            logger.info ("DataHandler: UpdateAce %s - %s to database , time elapsed %f s" % (identityName, resource, elapsed))
            return True
        except Exception as e:
            logger.error('Exception: '+ str(e))
            return False


    def UpdateAclIdentityId(self, identityName, identityId):
        try:
            start_time = timeit.default_timer()
            cursor = self.conn.cursor()
            sql = """update `%s` set identityId = '%s' where `identityName` = '%s' """ % (self.acltablename, identityId, identityName)
            cursor.execute(sql)

            self.conn.commit()
            cursor.close()
            elapsed = timeit.default_timer() - start_time
            logger.info ("DataHandler: UpdateAclIdentityId %s - %s to database , time elapsed %f s" % (identityName, identityId, elapsed))
            return True
        except Exception as e:
            logger.error('Exception: '+ str(e))
            return False


    def DeleteResourceAcl(self, resource):
        try:
            start_time = timeit.default_timer()
            cursor = self.conn.cursor()

            sql = "DELETE FROM `%s` WHERE `resource` = '%s'" % (self.acltablename, resource)
            cursor.execute(sql)

            self.conn.commit()
            cursor.close()
            elapsed = timeit.default_timer() - start_time
            logger.info ("DataHandler: DeleteResourceAcl %s, time elapsed %f s" % (resource, elapsed))
            return True
        except Exception as e:
            logger.error('Exception: '+ str(e))
            return False


    def DeleteAce(self, identityName, resource):
        try:
            start_time = timeit.default_timer()
            cursor = self.conn.cursor()

            sql = "DELETE FROM `%s` WHERE `identityName` = '%s' and `resource` = '%s'" % (self.acltablename, identityName, resource)
            cursor.execute(sql)

            self.conn.commit()
            cursor.close()
            elapsed = timeit.default_timer() - start_time
            logger.info ("DataHandler: DeleteAce %s : %s time elapsed %f s" % (resource, identityName, elapsed))
            return True
        except Exception as e:
            logger.error('Exception: '+ str(e))
            return False


    def GetAcl(self):
        start_time = timeit.default_timer()
        cursor = self.conn.cursor()
        query = "SELECT `identityName`,`identityId`,`resource`,`permissions`,`isDeny` FROM `%s`" % (self.acltablename)
        ret = []
        try:
            cursor.execute(query)
            for (identityName,identityId,resource,permissions,isDeny) in cursor:
                record = {}
                record["identityName"] = identityName
                record["identityId"] = identityId
                record["resource"] = resource
                record["permissions"] = permissions
                record["isDeny"] = isDeny
                ret.append(record)
        except Exception as e:
            logger.error('Exception: '+ str(e))
            pass
        self.conn.commit()
        cursor.close()
        elapsed = timeit.default_timer() - start_time
        logger.info ("DataHandler: GetAcl time elapsed %f s" % ( elapsed))
        return ret


    def GetResourceAcl(self, resource):
        start_time = timeit.default_timer()
        cursor = self.conn.cursor()
        query = "SELECT `identityName`,`identityId`,`resource`,`permissions`,`isDeny` FROM `%s` where `resource` = '%s'" % (self.acltablename, resource)
        ret = []
        try:
            cursor.execute(query)
            for (identityName,identityId,resource,permissions,isDeny) in cursor:
                record = {}
                record["identityName"] = identityName
                record["identityId"] = identityId
                record["resource"] = resource
                record["permissions"] = permissions
                record["isDeny"] = isDeny
                ret.append(record)
        except Exception as e:
            logger.error('Exception: '+ str(e))
            pass
        self.conn.commit()
        cursor.close()
        elapsed = timeit.default_timer() - start_time
        logger.info ("DataHandler: GetResourceAcl time elapsed %f s" % ( elapsed))
        return ret


    def AddJob(self, jobParams):
        try:
            start_time = timeit.default_timer()
            sql = "INSERT INTO `"+self.jobtablename+"` (jobId, familyToken, isParent, jobName, userName, vcName, jobType,jobParams ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"
            cursor = self.conn.cursor()
            jobParam = base64.b64encode(json.dumps(jobParams))
            cursor.execute(sql, (jobParams["jobId"], jobParams["familyToken"], jobParams["isParent"], jobParams["jobName"], jobParams["userName"], jobParams["vcName"], jobParams["jobType"],jobParam))
            self.conn.commit()
            cursor.close()
            elapsed = timeit.default_timer() - start_time
            logger.info("DataHandler: added job %s to database, time elapsed %f s" % (jobParams["jobId"], elapsed))
            return True
        except Exception as e:
           logger.error('Exception: '+ str(e))
           return False


    def GetJobList(self, userName, vcName, num = None, status = None, op = ("=","or")):
        start_time = timeit.default_timer()
        ret = []
        cursor = self.conn.cursor()
        try:
            query = "SELECT `jobId`,`jobName`,`userName`, `vcName`, `jobStatus`, `jobStatusDetail`, `jobType`, `jobDescriptionPath`, `jobDescription`, `jobTime`, `endpoints`, `jobParams`,`errorMsg` ,`jobMeta` FROM `%s` where `vcName` = '%s'" % (self.jobtablename, vcName)
            if userName != "all":
                query += " and `userName` = '%s'" % userName
            if status is not None:
                if "," not in status:
                    query += " and `jobStatus` %s '%s'" % (op[0], status)
                else:
                    status_list = [" `jobStatus` %s '%s' " % (op[0], s) for s in status.split(',')]
                    status_statement = (" "+op[1]+" ").join(status_list)
                    query += " and ( %s ) " % status_statement

            query += " order by `jobTime` Desc"

            if num is not None:
                query += " limit %s " % str(num)

            start_time1 = timeit.default_timer()
            cursor.execute(query)
            elapsed1 = timeit.default_timer() - start_time1
            start_time2 = timeit.default_timer()
            data = cursor.fetchall()
            elapsed2 = timeit.default_timer() - start_time2
            logger.info ("(fetchall time: %f)" % (elapsed2))
            for (jobId,jobName,userName, vcName, jobStatus,jobStatusDetail, jobType, jobDescriptionPath, jobDescription, jobTime, endpoints, jobParams,errorMsg, jobMeta) in data:
                record = {}
                record["jobId"] = jobId
                record["jobName"] = jobName
                record["userName"] = userName
                record["vcName"] = vcName
                record["jobStatus"] = jobStatus
                record["jobStatusDetail"] = jobStatusDetail
                record["jobType"] = jobType
                record["jobDescriptionPath"] = jobDescriptionPath
                record["jobDescription"] = jobDescription
                record["jobTime"] = jobTime
                record["endpoints"] = endpoints
                record["jobParams"] = jobParams
                record["errorMsg"] = errorMsg
                record["jobMeta"] = jobMeta
                ret.append(record)
        except Exception as e:
            logger.error('Exception: '+ str(e))
            pass
        self.conn.commit()
        cursor.close()
        elapsed = timeit.default_timer() - start_time
        logger.info("DataHandler: get job list for user %s , time elapsed %f s (SQL query time: %f)" % (userName, elapsed, elapsed1))
        return ret

    def GetJob(self, **kwargs):
        start_time = timeit.default_timer()
        valid_keys = ["jobId", "familyToken", "isParent", "jobName", "userName", "vcName", "jobStatus", "jobType", "jobTime"]
        if len(kwargs) != 1: return []
        key, expected = kwargs.popitem()
        if key not in valid_keys:
            logger.error("DataHandler_GetJob: key is not in valid keys list...")
            return []
        cursor = self.conn.cursor()
        query = "SELECT `jobId`,`familyToken`,`isParent`,`jobName`,`userName`, `vcName`, `jobStatus`, `jobStatusDetail`, `jobType`, `jobDescriptionPath`, `jobDescription`, `jobTime`, `endpoints`, `jobParams`,`errorMsg` ,`jobMeta`  FROM `%s` where `%s` = '%s' " % (self.jobtablename,key,expected)
        cursor.execute(query)
        columns = [column[0] for column in cursor.description]
        ret = [dict(zip(columns, row)) for row in cursor.fetchall()]
        self.conn.commit()
        cursor.close()
        elapsed = timeit.default_timer() - start_time
        logger.info("DataHandler: get job details with query %s=%s , time elapsed %f s" % (key, expected, elapsed))
        return ret

    def AddCommand(self, jobId, command):
        try:
            start_time = timeit.default_timer()
            sql = "INSERT INTO `"+self.commandtablename+"` (jobId, command) VALUES (%s,%s)"
            cursor = self.conn.cursor()
            cursor.execute(sql, (jobId, command))
            self.conn.commit()
            cursor.close()
            elapsed = timeit.default_timer() - start_time
            logger.info("DataHandler: add command to database, jobId: %s , time elapsed %f s" % (jobId, elapsed))
            return True
        except Exception as e:
            logger.error('Exception: '+ str(e))
            return False

    def GetPendingCommands(self):
        start_time = timeit.default_timer()
        cursor = self.conn.cursor()
        query = "SELECT `id`, `jobId`, `command` FROM `%s` WHERE `status` = 'pending' order by `time`" % (self.commandtablename)
        cursor.execute(query)
        ret = []
        for (id, jobId, command) in cursor:
            record = {}
            record["id"] = id
            record["jobId"] = jobId
            record["command"] = command
            ret.append(record)
        self.conn.commit()
        cursor.close()
        elapsed = timeit.default_timer() - start_time
        logger.info("DataHandler: get pending command , time elapsed %f s" % (elapsed))
        return ret

    def FinishCommand(self, commandId):
        try:
            start_time = timeit.default_timer()
            sql = """update `%s` set status = 'run' where `id` = '%s' """ % (self.commandtablename, commandId)
            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()
            elapsed = timeit.default_timer() - start_time
            logger.info("DataHandler: set command %s as finished , time elapsed %f s" % (commandId, elapsed))
            return True
        except Exception as e:
            logger.error('Exception: '+ str(e))
            return False

    def GetCommands(self, jobId):
        start_time = timeit.default_timer()
        cursor = self.conn.cursor()
        query = "SELECT `time`, `command`, `status`, `output` FROM `%s` WHERE `jobId` = '%s' order by `time`" % (self.commandtablename, jobId)
        cursor.execute(query)
        ret = []
        for (time, command, status, output) in cursor:
            record = {}
            record["time"] = time
            record["command"] = command
            record["status"] = status
            record["output"] = output
            ret.append(record)
        self.conn.commit()
        cursor.close()
        elapsed = timeit.default_timer() - start_time
        logger.info("DataHandler: get command list for job %s , time elapsed %f s" % (jobId, elapsed))
        return ret

    def load_json(self, raw_str):
        if isinstance(raw_str, unicode):
            raw_str = str(raw_str)
        try:
            return json.loads(raw_str)
        except:
            return {}

    def GetPendingEndpoints(self):
        try:
            start_time = timeit.default_timer()
            jobs = self.GetJob(jobStatus="running")

            # [ {endpoint1:{},endpoint2:{}}, {endpoint3:{}, ... }, ... ]
            endpoints = map(lambda job: self.load_json(job["endpoints"]), jobs)
            # {endpoint1: {}, endpoint2: {}, ... }
            # endpoint["status"] == "pending"
            pendingEndpoints = {k: v for d in endpoints for k, v in d.items() if v["status"] == "pending"}

            elapsed = timeit.default_timer() - start_time
            logger.info("DataHandler: get pending endpoints %d, time elapsed %f s" % (len(pendingEndpoints), elapsed))
            return pendingEndpoints
        except Exception as e:
            logger.exception("Query pending endpoints failed!")
            return {}

    def GetDeadEndpoints(self):
        try:
            start_time = timeit.default_timer()
            cursor = self.conn.cursor()
            # TODO we need job["lastUpdated"] for filtering
            query = "SELECT `endpoints` FROM jobs WHERE `jobStatus` <> 'running' order by `jobTime` DESC"
            cursor.execute(query)
            dead_endpoints = {}
            for [endpoints] in cursor:
                endpoint_list = {k: v for k, v in self.load_json(endpoints).items() if v["status"] == "running"}
                dead_endpoints.update(endpoint_list)
            self.conn.commit()
            cursor.close()
            elapsed = timeit.default_timer() - start_time
            logger.info("DataHandler: get dead endpoints %d , time elapsed %f s" % (len(dead_endpoints), elapsed))
            return dead_endpoints
        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.exception("Query dead endpoints failed!")
            return {}

    def UpdateEndpoint(self, endpoint):
        try:
            start_time = timeit.default_timer()
            job_id = endpoint["jobId"]
            job = self.GetJob(jobId=job_id)[0]
            job_endpoints = self.load_json(job["endpoints"])

            # update jobEndpoints
            job_endpoints[endpoint["id"]] = endpoint

            sql = "UPDATE jobs SET endpoints=%s where jobId=%s"
            cursor = self.conn.cursor()
            cursor.execute(sql, (json.dumps(job_endpoints), job_id))
            self.conn.commit()
            cursor.close()
            elapsed = timeit.default_timer() - start_time
            logger.info("DataHandler: update endpoints to database, endpointId: %s , time elapsed %f s" % (endpoint["id"], elapsed))
            return True
        except Exception as e:
            logger.exception("Update endpoints failed!")
            return False

    def GetPendingJobs(self):
        start_time = timeit.default_timer()
        cursor = self.conn.cursor()
        query = "SELECT `jobId`,`jobName`,`userName`, `vcName`, `jobStatus`, `jobType`, `jobDescriptionPath`, `jobDescription`, `jobTime`, `endpoints`, `jobParams`,`errorMsg` ,`jobMeta` FROM `%s` where `jobStatus` <> 'error' and `jobStatus` <> 'failed' and `jobStatus` <> 'finished' and `jobStatus` <> 'killed' order by `jobTime` DESC" % (self.jobtablename)
        cursor.execute(query)
        ret = []
        for (jobId,jobName,userName,vcName, jobStatus, jobType, jobDescriptionPath, jobDescription, jobTime, endpoints, jobParams,errorMsg, jobMeta) in cursor:
            record = {}
            record["jobId"] = jobId
            record["jobName"] = jobName
            record["userName"] = userName
            record["vcName"] = vcName
            record["jobStatus"] = jobStatus
            record["jobType"] = jobType
            record["jobDescriptionPath"] = jobDescriptionPath
            record["jobDescription"] = jobDescription
            record["jobTime"] = jobTime
            record["endpoints"] = endpoints
            record["jobParams"] = jobParams
            record["errorMsg"] = errorMsg
            record["jobMeta"] = jobMeta
            ret.append(record)
        self.conn.commit()
        cursor.close()
        elapsed = timeit.default_timer() - start_time
        logger.info("DataHandler: get pending jobs %d, time elapsed %f s" % (len(ret), elapsed))
        return ret



    def SetJobError(self, jobId, errorMsg):
        try:
            start_time = timeit.default_timer()
            sql = """update `%s` set jobStatus = 'error', `errorMsg` = '%s' where `jobId` = '%s' """ % (self.jobtablename, errorMsg, jobId)
            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()
            elapsed = timeit.default_timer() - start_time
            logger.info("DataHandler: set job %s error status in database, time elapsed %f s" % (jobId, elapsed))
            return True
        except Exception as e:
            logger.error('Exception: '+ str(e))
            return False

    def UpdateJobTextField(self, jobId, field, value):
        try:
            start_time = timeit.default_timer()
            sql = "update `%s` set `%s` = '%s' where `jobId` = '%s' " % (self.jobtablename, field, value, jobId)
            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()
            elapsed = timeit.default_timer() - start_time
            logger.info ("DataHandler: update job %s, field %s to %s, time elapsed %f s" % (jobId, field, value, elapsed))
            return True
        except Exception as e:
            logger.error('Exception: '+ str(e))
            return False

    def GetJobTextField(self, jobId, field):
        start_time = timeit.default_timer()
        cursor = self.conn.cursor()
        query = "SELECT `jobId`, `%s` FROM `%s` where `jobId` = '%s' " % (field, self.jobtablename, jobId)
        ret = None
        try:
            cursor.execute(query)
            for (jobId, value) in cursor:
                ret = value
        except Exception as e:
            logger.error('Exception: '+ str(e))
            pass
        self.conn.commit()
        cursor.close()
        elapsed = timeit.default_timer() - start_time
        logger.info("DataHandler: get filed %s of job %s , time elapsed %f s" % (field, jobId, elapsed))
        return ret

    def AddandGetJobRetries(self, jobId):
        start_time = timeit.default_timer()
        sql = """update `%s` set `retries` = `retries` + 1 where `jobId` = '%s' """ % (self.jobtablename, jobId)
        cursor = self.conn.cursor()
        cursor.execute(sql)
        self.conn.commit()
        cursor.close()

        cursor = self.conn.cursor()
        query = "SELECT `jobId`, `retries` FROM `%s` where `jobId` = '%s' " % (self.jobtablename, jobId)
        cursor.execute(query)
        ret = None

        for (jobId, value) in cursor:
            ret = value
        self.conn.commit()
        cursor.close()
        elapsed = timeit.default_timer() - start_time
        logger.info("DataHandler: get and update retries for job %s , time elapsed %f s" % (jobId, elapsed))
        return ret

    def UpdateClusterStatus(self, clusterStatus):
        try:
            status = base64.b64encode(json.dumps(clusterStatus))

            start_time = timeit.default_timer()
            sql = "INSERT INTO `%s` (status) VALUES ('%s')" % (self.clusterstatustablename, status)
            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()
            elapsed = timeit.default_timer() - start_time
            logger.info("DataHandler: update cluster status, time elapsed %f s" % (elapsed))
            return True
        except Exception as e:
            logger.error('Exception: '+ str(e))
            return False

    def GetClusterStatus(self):
        start_time = timeit.default_timer()
        cursor = self.conn.cursor()
        query = "SELECT `time`, `status` FROM `%s` order by `time` DESC limit 1" % (self.clusterstatustablename)
        ret = None
        time = None
        try:
            cursor.execute(query)
            for (t, value) in cursor:
                ret = json.loads(base64.b64decode(value))
                time = t
        except Exception as e:
            logger.error('Exception: '+ str(e))
            pass
        self.conn.commit()
        cursor.close()
        elapsed = timeit.default_timer() - start_time
        logger.info("DataHandler: get cluster status , time elapsed %f s" % (elapsed))
        return ret, time


    def GetUsers(self):
        start_time = timeit.default_timer()
        cursor = self.conn.cursor()
        query = "SELECT `identityName`,`uid` FROM `%s`" % (self.identitytablename)
        ret = []
        try:
            cursor.execute(query)
            for (identityName,uid) in cursor:
                ret.append((identityName,uid))
        except Exception as e:
            logger.error('Exception: '+ str(e))
            pass
        self.conn.commit()
        cursor.close()
        elapsed = timeit.default_timer() - start_time
        logger.info("DataHandler: get users, time elapsed %f s" % (elapsed))
        return ret

    def GetActiveJobsCount(self):
        cursor = self.conn.cursor()
        query = "SELECT count(ALL id) as c FROM `%s` where `jobStatus` <> 'error' and `jobStatus` <> 'failed' and `jobStatus` <> 'finished' and `jobStatus` <> 'killed' " % (self.jobtablename)
        cursor.execute(query)
        ret = 0
        for c in cursor:
            ret = c[0]
        self.conn.commit()
        cursor.close()

        return ret

    def GetALLJobsCount(self):
        cursor = self.conn.cursor()
        query = "SELECT count(ALL id) as c FROM `%s`" % (self.jobtablename)
        cursor.execute(query)
        ret = 0
        for c in cursor:
            ret = c[0]
        self.conn.commit()
        cursor.close()

        return ret

    def __del__(self):
        logger.debug("********************** deleted a DataHandler instance *******************")
        self.Close()

    def Close(self):
        ### !!! DataHandler is not threadsafe object, a same object cannot be used in multiple threads
        try:
            self.conn.close()
        except Exception as e:
            pass


if __name__ == '__main__':
    TEST_INSERT_JOB = False
    TEST_QUERY_JOB_LIST = False
    CREATE_TABLE = False
    CREATE_DB = True
    dataHandler = DataHandler()
    print dataHandler.GetJobList("hongzl@microsoft.com", num=1)
    if TEST_INSERT_JOB:
        jobParams = {}
        jobParams["id"] = "dist-tf-00001"
        jobParams["job-name"] = "dist-tf"
        jobParams["user-id"] = "hongzl"
        jobParams["job-meta-path"] = "/dlws/jobfiles/***"
        jobParams["job-meta"] = "ADSCASDcAE!EDASCASDFD"

        dataHandler.AddJob(jobParams)

    if CREATE_TABLE:
        dataHandler.CreateTable()

    if CREATE_DB:
        dataHandler.CreateDatabase()
