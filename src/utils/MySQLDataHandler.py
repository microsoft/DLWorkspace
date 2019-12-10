import mysql.connector
import json
import base64
import os
import logging
import functools

import timeit

from Queue import Queue

from config import config
from config import global_vars

from prometheus_client import Histogram

logger = logging.getLogger(__name__)

data_handler_fn_histogram = Histogram("datahandler_fn_latency_seconds",
        "latency for executing data handler function (seconds)",
        buckets=(.05, .075, .1, .25, .5, .75, 1.0, 2.5, 5.0,
            7.5, 10.0, 12.5, 15.0, 17.5, 20.0, float("inf")),
        labelnames=("fn_name",))

db_connect_histogram = Histogram("db_connect_latency_seconds",
        "latency for connecting to db (seconds)",
        buckets=(.05, .075, .1, .25, .5, .75, 1.0, 2.5, 5.0, 7.5, float("inf")))


def record(fn):
    @functools.wraps(fn)
    def wrapped(*args, **kwargs):
        start = timeit.default_timer()
        try:
            return fn(*args, **kwargs)
        finally:
            elapsed = timeit.default_timer() - start
            data_handler_fn_histogram.labels(fn.__name__).observe(elapsed)
    return wrapped


class DataHandler(object):
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
        self.templatetablename = "templates"
        self.jobprioritytablename = "job_priorities"
        server = config["mysql"]["hostname"]
        username = config["mysql"]["username"]
        password = config["mysql"]["password"]

        self.CreateDatabase()

        with db_connect_histogram.time():
            self.conn = mysql.connector.connect(user=username, password=password,
                                                host=server, database=self.database)

        self.CreateTable()

        elapsed = timeit.default_timer() - start_time

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

            # when the VC has vm of same GPU type but different VMsizes, e.g., when VC has Standard_NC6s_v3 and Standard_NC12s_v3 both?
            # impossible since there's no way to do it with current config mechanism

            gpu_count_per_node = config["gpu_count_per_node"]
            worker_node_num = config["worker_node_num"]
            gpu_type = config["gpu_type"]

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
                AS SELECT \'%s\' AS vcName, NULL AS parent, '{\\\"%s\\\":%s}' AS quota, '{\\\"%s\\\":{\\\"num_gpu_per_node\\\":%s}}' AS metadata;
                """ % (self.vctablename, self.vctablename, config['defalt_virtual_cluster_name'], gpu_type, gpu_count_per_node*worker_node_num, gpu_type,gpu_count_per_node)

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


            sql = """
                CREATE TABLE IF NOT EXISTS `%s`
                (
                    `id`    INT          NOT NULL AUTO_INCREMENT,
                    `name`  VARCHAR(255) NOT NULL,
                    `scope` VARCHAR(255) NOT NULL COMMENT '"master", "vc:vcname" or "user:username"',
                    `json`  TEXT         NOT NULL,
                    `time`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (`id`),
                    CONSTRAINT name_scope UNIQUE(`name`, `scope`)
                )
                """ % (self.templatetablename)

            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()


            sql = """
                CREATE TABLE IF NOT EXISTS  `%s`
                (
                    `id`             INT     NOT NULL AUTO_INCREMENT,
                    `jobId`   varchar(50)   NOT NULL,
                    `priority`     INT NOT NULL,
                    `time`           DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    PRIMARY KEY (`id`),
                    CONSTRAINT identityName_jobId UNIQUE(`jobId`)
                )
                """ % (self.jobprioritytablename)

            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()

    @record
    def AddStorage(self, vcName, url, storageType, metadata, defaultMountPath):
        try:
            sql = "INSERT INTO `"+self.storagetablename+"` (storageType, url, metadata, vcName, defaultMountPath) VALUES (%s,%s,%s,%s,%s)"
            cursor = self.conn.cursor()
            cursor.execute(sql, (storageType, url, metadata, vcName, defaultMountPath))
            self.conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.error('Exception: %s', str(e))
            return False

    @record
    def DeleteStorage(self, vcName, url):
        try:
            sql = "DELETE FROM `%s` WHERE url = '%s' and vcName = '%s'" % (self.storagetablename, url, vcName)
            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.error('Exception: %s', str(e))
            return False

    @record
    def ListStorages(self, vcName):
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
            logger.error('Exception: %s', str(e))
            pass
        self.conn.commit()
        cursor.close()
        return ret


    @record
    def UpdateStorage(self, vcName, url, storageType, metadata, defaultMountPath):
        try:
            sql = """update `%s` set storageType = '%s', metadata = '%s', defaultMountPath = '%s' where vcName = '%s' and url = '%s' """ % (self.storagetablename, storageType, metadata, defaultMountPath, vcName, url)
            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.error('Exception: %s', str(e))
            return False


    @record
    def AddVC(self, vcName, quota, metadata):
        try:
            sql = "INSERT INTO `"+self.vctablename+"` (vcName, quota, metadata) VALUES (%s,%s,%s)"
            cursor = self.conn.cursor()
            cursor.execute(sql, (vcName, quota, metadata))
            self.conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.error('Exception: %s', str(e))
            return False


    @record
    def ListVCs(self):
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
            logger.error('Exception: %s', str(e))
            pass
        self.conn.commit()
        cursor.close()
        return ret


    @record
    def DeleteVC(self, vcName):
        try:
            sql = "DELETE FROM `%s` WHERE vcName = '%s'" % (self.vctablename, vcName)
            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.error('Exception: %s', str(e))
            return False


    @record
    def UpdateVC(self, vcName, quota, metadata):
        try:
            sql = """update `%s` set quota = '%s', metadata = '%s' where vcName = '%s' """ % (self.vctablename, quota, metadata, vcName)
            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.error('Exception: %s', str(e))
            return False


    @record
    def GetIdentityInfo(self, identityName):
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
            logger.error('GetIdentityInfo Exception: %s', str(e))
        self.conn.commit()
        cursor.close()
        return ret


    @record
    def UpdateIdentityInfo(self, identityName, uid, gid, groups):
        try:
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
            return True
        except Exception as e:
            logger.error('UpdateIdentityInfo Exception: %s', str(e))
            return False


    @record
    def GetAceCount(self, identityName, resource):
        cursor = self.conn.cursor()
        query = "SELECT count(ALL id) as c FROM `%s` where `identityName` = '%s' and `resource` = '%s'" % (self.acltablename,identityName, resource)
        cursor.execute(query)
        ret = 0
        for c in cursor:
            ret = c[0]
        self.conn.commit()
        cursor.close()
        return ret


    @record
    def UpdateAce(self, identityName, identityId, resource, permissions, isDeny):
        try:
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
            return True
        except Exception as e:
            logger.error('Exception: %s', str(e))
            return False


    @record
    def UpdateAclIdentityId(self, identityName, identityId):
        try:
            cursor = self.conn.cursor()
            sql = """update `%s` set identityId = '%s' where `identityName` = '%s' """ % (self.acltablename, identityId, identityName)
            cursor.execute(sql)

            self.conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.error('Exception: %s', str(e))
            return False


    @record
    def DeleteResourceAcl(self, resource):
        try:
            cursor = self.conn.cursor()

            sql = "DELETE FROM `%s` WHERE `resource` = '%s'" % (self.acltablename, resource)
            cursor.execute(sql)

            self.conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.error('Exception: %s', str(e))
            return False


    @record
    def DeleteAce(self, identityName, resource):
        try:
            cursor = self.conn.cursor()

            sql = "DELETE FROM `%s` WHERE `identityName` = '%s' and `resource` = '%s'" % (self.acltablename, identityName, resource)
            cursor.execute(sql)

            self.conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.error('Exception: %s', str(e))
            return False


    @record
    def GetAcl(self):
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
            logger.error('Exception: %s', str(e))
            pass
        self.conn.commit()
        cursor.close()
        return ret


    @record
    def GetResourceAcl(self, resource):
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
            logger.error('Exception: %s', str(e))
        self.conn.commit()
        cursor.close()
        return ret


    @record
    def AddJob(self, jobParams):
        try:
            sql = "INSERT INTO `"+self.jobtablename+"` (jobId, familyToken, isParent, jobName, userName, vcName, jobType,jobParams ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"
            cursor = self.conn.cursor()
            jobParam = base64.b64encode(json.dumps(jobParams))
            cursor.execute(sql, (jobParams["jobId"], jobParams["familyToken"], jobParams["isParent"], jobParams["jobName"], jobParams["userName"], jobParams["vcName"], jobParams["jobType"],jobParam))
            self.conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.error('Exception: %s', str(e))
            return False


    @record
    def GetJobList(self, userName, vcName, num = None, status = None, op = ("=","or")):
        ret = []
        cursor = self.conn.cursor()
        try:
            query = "SELECT `jobId`,`jobName`,`userName`, `vcName`, `jobStatus`, `jobStatusDetail`, `jobType`, `jobDescriptionPath`, `jobDescription`, `jobTime`, `endpoints`, `jobParams`,`errorMsg` ,`jobMeta` FROM `%s` where 1" % (self.jobtablename)
            if userName != "all":
                query += " and `userName` = '%s'" % userName

            if vcName != "all":
                query += " and `vcName` = '%s'" % vcName

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

            cursor.execute(query)

            data = cursor.fetchall()
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
            logger.error('Exception: %s', str(e))
        self.conn.commit()
        cursor.close()
        return ret

    @record
    def GetActiveJobList(self):
        ret = []
        cursor = self.conn.cursor()
        try:
            query = "SELECT `jobId`, `userName`, `vcName`, `jobParams`, `jobStatus` FROM `%s` WHERE `jobStatus` = 'scheduling' OR `jobStatus` = 'running'" % (self.jobtablename)

            cursor.execute(query)
            data = cursor.fetchall()

            for (jobId,userName,vcName,jobParams,jobStatus) in data:
                record = {}
                record["jobId"] = jobId
                record["userName"] = userName
                record["vcName"] = vcName
                record["jobParams"] = jobParams
                record["jobStatus"] = jobStatus
                ret.append(record)
        except Exception as e:
            logger.error('Exception: %s', str(e))
        self.conn.commit()
        cursor.close()
        return ret

    @record
    def GetJob(self, **kwargs):
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
        return ret

    @record
    def AddCommand(self, jobId, command):
        try:
            sql = "INSERT INTO `"+self.commandtablename+"` (jobId, command) VALUES (%s,%s)"
            cursor = self.conn.cursor()
            cursor.execute(sql, (jobId, command))
            self.conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.error('Exception: %s', str(e))
            return False

    @record
    def GetPendingCommands(self):
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
        return ret

    @record
    def FinishCommand(self, commandId):
        try:
            sql = """update `%s` set status = 'run' where `id` = '%s' """ % (self.commandtablename, commandId)
            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.error('Exception: %s', str(e))
            return False

    @record
    def GetCommands(self, jobId):
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
        return ret

    def load_json(self, raw_str):
        if isinstance(raw_str, unicode):
            raw_str = str(raw_str)
        try:
            return json.loads(raw_str)
        except:
            return {}

    @record
    def GetPendingEndpoints(self):
        try:
            jobs = self.GetJob(jobStatus="running")

            # [ {endpoint1:{},endpoint2:{}}, {endpoint3:{}, ... }, ... ]
            endpoints = map(lambda job: self.load_json(job["endpoints"]), jobs)
            # {endpoint1: {}, endpoint2: {}, ... }
            # endpoint["status"] == "pending"
            pendingEndpoints = {k: v for d in endpoints for k, v in d.items() if v["status"] == "pending"}

            return pendingEndpoints
        except Exception as e:
            logger.exception("Query pending endpoints failed!")
            return {}

    @record
    def GetJobEndpoints(self, job_id):
        try:
            jobs = self.GetJob(jobId=job_id)

            # [ {endpoint1:{},endpoint2:{}}, {endpoint3:{}, ... }, ... ]
            endpoints = map(lambda job: self.load_json(job["endpoints"]), jobs)
            # {endpoint1: {}, endpoint2: {}, ... }
            # endpoint["status"] == "pending"
            endpoints = {k: v for d in endpoints for k, v in d.items()}

            return endpoints
        except Exception as e:
            logger.warning("Query job endpoints failed! Job {}".format(job_id), exc_info=True)
            return {}

    @record
    def GetDeadEndpoints(self):
        try:
            cursor = self.conn.cursor()
            # TODO we need job["lastUpdated"] for filtering
            query = "SELECT `endpoints` FROM jobs WHERE `jobStatus` <> 'running' and `jobStatus` <> 'pending' and `jobStatus` <> 'queued' and `jobStatus` <> 'scheduling' order by `jobTime` DESC"
            cursor.execute(query)
            dead_endpoints = {}
            for [endpoints] in cursor:
                endpoint_list = {k: v for k, v in self.load_json(endpoints).items() if v["status"] == "running"}
                dead_endpoints.update(endpoint_list)
            self.conn.commit()
            cursor.close()
            return dead_endpoints
        except Exception as e:
            logger.exception("Query dead endpoints failed!")
            return {}

    @record
    def UpdateEndpoint(self, endpoint):
        try:
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
            return True
        except Exception as e:
            logger.exception("Update endpoints failed! Endpoints: {}".format(endpoint))
            return False

    @record
    def GetPendingJobs(self):
        cursor = self.conn.cursor()
        query = "SELECT `jobId`,`jobName`,`userName`, `vcName`, `jobStatus`, `jobStatusDetail`, `jobType`, `jobDescriptionPath`, `jobDescription`, `jobTime`, `endpoints`, `jobParams`,`errorMsg` ,`jobMeta` FROM `%s` where `jobStatus` <> 'error' and `jobStatus` <> 'failed' and `jobStatus` <> 'finished' and `jobStatus` <> 'killed' order by `jobTime` DESC" % (self.jobtablename)
        cursor.execute(query)
        ret = []
        for (jobId,jobName,userName,vcName, jobStatus, jobStatusDetail, jobType, jobDescriptionPath, jobDescription, jobTime, endpoints, jobParams,errorMsg, jobMeta) in cursor:
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
        self.conn.commit()
        cursor.close()
        return ret


    @record
    def SetJobError(self, jobId, errorMsg):
        try:
            sql = """update `%s` set jobStatus = 'error', `errorMsg` = '%s' where `jobId` = '%s' """ % (self.jobtablename, errorMsg, jobId)
            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.error('Exception: %s', str(e))
            return False

    @record
    def UpdateJobTextField(self, jobId, field, value):
        try:
            sql = "update `%s` set `%s` = '%s' where `jobId` = '%s' " % (self.jobtablename, field, value, jobId)
            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.error('Exception: %s', str(e))
            return False

    @record
    def GetJobTextField(self, jobId, field):
        cursor = self.conn.cursor()
        query = "SELECT `jobId`, `%s` FROM `%s` where `jobId` = '%s' " % (field, self.jobtablename, jobId)
        ret = None
        try:
            cursor.execute(query)
            for (jobId, value) in cursor:
                ret = value
        except Exception as e:
            logger.error('Exception: %s', str(e))
            pass
        self.conn.commit()
        cursor.close()
        return ret

    @record
    def AddandGetJobRetries(self, jobId):
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
        return ret

    @record
    def UpdateClusterStatus(self, clusterStatus):
        try:
            status = base64.b64encode(json.dumps(clusterStatus))

            sql = "INSERT INTO `%s` (status) VALUES ('%s')" % (self.clusterstatustablename, status)
            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.error('Exception: %s', str(e))
            return False

    @record
    def GetClusterStatus(self):
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
            logger.error('Exception: %s', str(e))
        self.conn.commit()
        cursor.close()
        return ret, time


    @record
    def GetUsers(self):
        cursor = self.conn.cursor()
        query = "SELECT `identityName`,`uid` FROM `%s`" % (self.identitytablename)
        ret = []
        try:
            cursor.execute(query)
            for (identityName,uid) in cursor:
                ret.append((identityName,uid))
        except Exception as e:
            logger.error('Exception: %s', str(e))
        self.conn.commit()
        cursor.close()
        return ret

    @record
    def GetActiveJobsCount(self):
        cursor = self.conn.cursor()
        query = "SELECT count(ALL id) as c FROM `%s` where `jobStatus` = 'running'" % (self.jobtablename)
        cursor.execute(query)
        ret = 0
        for c in cursor:
            ret = c[0]
        self.conn.commit()
        cursor.close()

        return ret

    @record
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

    @record
    def GetTemplates(self, scope):
        cursor = self.conn.cursor()
        query = "SELECT `name`, `json` FROM `%s` WHERE `scope` = '%s'" % (self.templatetablename, scope)
        cursor.execute(query)
        ret = []
        for name, json in cursor:
            record = {}
            record["name"] = name
            record["json"] = json
            ret.append(record)
        self.conn.commit()
        cursor.close()
        return ret

    @record
    def UpdateTemplate(self, name, scope, json):
        try:
            cursor = self.conn.cursor()
            query = "INSERT INTO `" + self.templatetablename + "`(`name`, `scope`, `json`) VALUES(%s, %s, %s) ON DUPLICATE KEY UPDATE `json` = %s"
            cursor.execute(query, (name, scope, json, json))
            self.conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.error('Exception: %s', str(e))
            return False

    @record
    def DeleteTemplate(self, name, scope):
        try:
            cursor = self.conn.cursor()
            query = "DELETE FROM `" + self.templatetablename + "` WHERE `name` = %s and `scope` = %s"
            cursor.execute(query, (name, scope))
            self.conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.error('Exception: %s', str(e))
            return False

    @record
    def get_job_priority(self):
        cursor = self.conn.cursor()
        query = "select jobId, priority from {} where jobId in (select jobId from {} where jobStatus in (\"queued\", \"scheduling\", \"running\", \"unapproved\", \"pausing\", \"paused\"))".format(self.jobprioritytablename, self.jobtablename)
        cursor.execute(query)
        priority_dict = {}
        for job_id, priority in cursor:
            priority_dict[job_id] = priority
        self.conn.commit()
        cursor.close()

        return priority_dict

    @record
    def update_job_priority(self, job_priorites):
        cursor = self.conn.cursor()
        for job_id, priority in job_priorites.items():
            query = "INSERT INTO {0}(jobId, priority, time) VALUES('{1}', {2}, SYSDATE()) ON DUPLICATE KEY UPDATE jobId='{1}', priority='{2}' ".format(self.jobprioritytablename, job_id, priority)
            cursor.execute(query)
        self.conn.commit()
        cursor.close()
        return True

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
