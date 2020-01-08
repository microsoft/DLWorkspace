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

import MySQLdb
from DBUtils.PooledDB import PooledDB
import threading

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
            logger.info("DataHandler: %s, time elapsed %.2fs", fn.__name__, elapsed)
            data_handler_fn_histogram.labels(fn.__name__).observe(elapsed)
    return wrapped

class SingletonDBPool(object):
    __instance_lock = threading.Lock()

    def __init__(self, *args, **kwargs):
        database = "DLWSCluster-%s" % config["clusterId"]
        server = config["mysql"]["hostname"]
        username = config["mysql"]["username"]
        password = config["mysql"]["password"]
        with db_connect_histogram.time():
            self.pool = PooledDB(creator=MySQLdb, maxconnections=150, blocking=False,
                            host=server, db=database, user=username, passwd=password)
            logger.info("init MySQL DBUtils pool succeed")

    @classmethod     
    def instance(cls, *args, **kwargs):
        if not hasattr(SingletonDBPool, "_instance"):
            with SingletonDBPool.__instance_lock:
                if not hasattr(SingletonDBPool, "_instance"):
                    SingletonDBPool._instance = SingletonDBPool(*args, **kwargs)
        return SingletonDBPool._instance
    
    def get_connection(self):
        return self.pool.connection()

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
        self.pool = SingletonDBPool.instance()
        elapsed = timeit.default_timer() - start_time
        logger.info("DB Utils DataHandler initialization, time elapsed %f s", elapsed)

    def CreateDatabase(self):
        if "initSQLDB" not in global_vars or not global_vars["initSQLDB"]:
            logger.info("===========init SQL database===============")
            global_vars["initSQLDB"] = True

            conn = self.pool.get_connection()
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

            conn = self.pool.get_connection()
            cursor = conn.cursor()
            cursor.execute(sql)
            conn.commit()
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

            cursor = conn.cursor()
            cursor.execute(sql)
            conn.commit()
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

            cursor = conn.cursor()
            cursor.execute(sql)
            conn.commit()
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

            cursor = conn.cursor()
            cursor.execute(sql)
            conn.commit()
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

            cursor = conn.cursor()
            cursor.execute(sql)
            conn.commit()
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

            cursor = conn.cursor()
            cursor.execute(sql)
            conn.commit()
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

            cursor = conn.cursor()
            cursor.execute(sql)
            conn.commit()
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

            cursor = conn.cursor()
            cursor.execute(sql)
            conn.commit()
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

            cursor = conn.cursor()
            cursor.execute(sql)
            conn.commit()
            cursor.close()
            conn.close()

    @record
    def AddStorage(self, vcName, url, storageType, metadata, defaultMountPath):
        ret = False
        conn = None
        cursor = None
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()
            
            sql = "INSERT INTO `"+self.storagetablename+"` (storageType, url, metadata, vcName, defaultMountPath) VALUES (%s,%s,%s,%s,%s)"
            cursor.execute(sql, (storageType, url, metadata, vcName, defaultMountPath))
            conn.commit()
            ret = True
        except Exception as e:
            logger.error('AddStorage Exception: %s', str(e))
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
        return ret
            

    @record
    def DeleteStorage(self, vcName, url):
        ret = False
        conn = None
        cursor = None
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()
            
            sql = "DELETE FROM `%s` WHERE url = '%s' and vcName = '%s'" % (self.storagetablename, url, vcName)
            cursor.execute(sql)
            conn.commit()
            ret = True
        except Exception as e:
            logger.error('DeleteStorage Exception: %s', str(e))
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
        return ret

    @record
    def ListStorages(self, vcName):
        ret = []
        conn = None
        cursor = None
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()
            
            query = "SELECT `storageType`,`url`,`metadata`,`vcName`,`defaultMountPath` FROM `%s` WHERE vcName = '%s' " % (self.storagetablename, vcName)
            cursor.execute(query)
            for (storageType,url,metadata,vcName,defaultMountPath) in cursor:
                record = {}
                record["vcName"] = vcName
                record["url"] = url
                record["storageType"] = storageType
                record["metadata"] = metadata
                record["defaultMountPath"] = defaultMountPath
                ret.append(record)
            conn.commit()
        except Exception as e:
            logger.error('ListStorages Exception: %s', str(e))
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
        return ret

    @record
    def UpdateStorage(self, vcName, url, storageType, metadata, defaultMountPath):
        ret = False
        conn = None
        cursor = None
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()
            
            sql = """update `%s` set storageType = '%s', metadata = '%s', defaultMountPath = '%s' where vcName = '%s' and url = '%s' """ % (self.storagetablename, storageType, metadata, defaultMountPath, vcName, url)
            cursor.execute(sql)
            conn.commit()
            ret = True
        except Exception as e:
            logger.error('UpdateStorage Exception: %s', str(e))
            ret = False
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
        return ret

    @record
    def AddVC(self, vcName, quota, metadata):
        ret = False
        conn = None
        cursor = None
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()
            
            sql = "INSERT INTO `"+self.vctablename+"` (vcName, quota, metadata) VALUES (%s,%s,%s)"
            cursor.execute(sql, (vcName, quota, metadata))
            conn.commit()
            ret = True
        except Exception as e:
            logger.error('AddVC Exception: %s', str(e))
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
        return ret


    @record
    def ListVCs(self):
        ret = []
        conn = None
        cursor = None
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()

            query = "SELECT `vcName`,`quota`,`metadata` FROM `%s`" % (self.vctablename)
            cursor.execute(query)
            for (vcName,quota,metadata) in cursor:
                record = {}
                record["vcName"] = vcName
                record["quota"] = quota
                record["metadata"] = metadata
                ret.append(record)
            conn.commit()
        except Exception as e:
            logger.error('ListVCs Exception: %s', str(e))
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
        return ret

    @record
    def DeleteVC(self, vcName):
        ret = False
        conn = None
        cursor = None
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()
            
            sql = "DELETE FROM `%s` WHERE vcName = '%s'" % (self.vctablename, vcName)
            cursor.execute(sql)
            conn.commit()
            ret = True
        except Exception as e:
            logger.error('DeleteVC Exception: %s', str(e))
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
        return ret


    @record
    def UpdateVC(self, vcName, quota, metadata):
        ret = False
        conn = None
        cursor = None
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()
            
            sql = """update `%s` set quota = '%s', metadata = '%s' where vcName = '%s' """ % (self.vctablename, quota, metadata, vcName)
            cursor.execute(sql)
            conn.commit()
            ret = True
        except Exception as e:
            logger.error('UpdateVC Exception: %s', str(e))
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
        return ret


    @record
    def GetIdentityInfo(self, identityName):
        ret = []
        conn = None
        cursor = None
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()
            query = "SELECT `identityName`,`uid`,`gid`,`groups` FROM `%s` where `identityName` = '%s'" % (self.identitytablename, identityName)
            cursor.execute(query)
            for (identityName,uid,gid,groups) in cursor:
                record = {}
                record["identityName"] = identityName
                record["uid"] = uid
                record["gid"] = gid
                record["groups"] = json.loads(groups)
                ret.append(record)
            conn.commit()
        except Exception as e:
            logger.error('GetIdentityInfo Exception: %s', str(e))
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
        return ret


    @record
    def UpdateIdentityInfo(self, identityName, uid, gid, groups):
        ret = False
        conn = None
        cursor = None
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()
            
            if (isinstance(groups, list)):
                groups = json.dumps(groups)

            sql = "insert into {0} (identityName, uid, gid, groups) values ('{1}', '{2}', '{3}', '{4}') on duplicate key update uid='{2}', gid='{3}', groups='{4}'".format(self.identitytablename, identityName, uid, gid, groups)
            cursor.execute(sql)

            conn.commit()
            ret = True
        except Exception as e:
            logger.error('UpdateIdentityInfo Exception: %s', str(e))
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
        return ret


    @record
    def UpdateAce(self, identityName, identityId, resource, permissions, isDeny):
        ret = False
        conn = None
        cursor = None
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()
            
            sql = "insert into {0} (identityName, identityId, resource, permissions, isDeny) values ('{1}', '{2}', '{3}', '{4}', '{5}') on duplicate key update permissions='{4}'".format(self.acltablename, identityName, identityId, resource, permissions, isDeny)
            cursor.execute(sql)

            conn.commit()
            ret = True
        except Exception as e:
            logger.error('UpdateAce Exception: %s', str(e))
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
        return ret


    @record
    def UpdateAclIdentityId(self, identityName, identityId):
        ret = False
        conn = None
        cursor = None
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()
            
            sql = """update `%s` set identityId = '%s' where `identityName` = '%s' """ % (self.acltablename, identityId, identityName)
            cursor.execute(sql)
            conn.commit()
            ret = True
        except Exception as e:
            logger.error('UpdateAclIdentityId Exception: %s', str(e))
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
        return ret


    @record
    def DeleteResourceAcl(self, resource):
        ret = False
        conn = None
        cursor = None
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()
            
            sql = "DELETE FROM `%s` WHERE `resource` = '%s'" % (self.acltablename, resource)
            cursor.execute(sql)

            conn.commit()
            ret = True
        except Exception as e:
            logger.error('DeleteResourceAcl Exception: %s', str(e))
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
        return ret


    @record
    def DeleteAce(self, identityName, resource):
        ret = False
        conn = None
        cursor = None
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()
            
            sql = "DELETE FROM `%s` WHERE `identityName` = '%s' and `resource` = '%s'" % (self.acltablename, identityName, resource)
            cursor.execute(sql)

            conn.commit()
            ret = True
        except Exception as e:
            logger.error('DeleteAce Exception: %s', str(e))
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
        return ret

    @record
    def GetAcl(self):
        ret = []
        conn = None
        cursor = None
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()
            
            query = "SELECT `identityName`,`identityId`,`resource`,`permissions`,`isDeny` FROM `%s`" % (self.acltablename)
            cursor.execute(query)
            for (identityName,identityId,resource,permissions,isDeny) in cursor:
                record = {}
                record["identityName"] = identityName
                record["identityId"] = identityId
                record["resource"] = resource
                record["permissions"] = permissions
                record["isDeny"] = isDeny
                ret.append(record)
            conn.commit()
        except Exception as e:
            logger.error('GetAcl Exception: %s', str(e))
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
        return ret

    @record
    def GetResourceAcl(self, resource):
        ret = []
        conn = None
        cursor = None
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()
            
            query = "SELECT `identityName`,`identityId`,`resource`,`permissions`,`isDeny` FROM `%s` where `resource` = '%s'" % (self.acltablename, resource)
            cursor.execute(query)
            for (identityName,identityId,resource,permissions,isDeny) in cursor:
                record = {}
                record["identityName"] = identityName
                record["identityId"] = identityId
                record["resource"] = resource
                record["permissions"] = permissions
                record["isDeny"] = isDeny
                ret.append(record)
            conn.commit()
        except Exception as e:
            logger.error('GetResourceAcl Exception: %s', str(e))
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
        return ret


    @record
    def AddJob(self, jobParams):
        ret = False
        conn = None
        cursor = None
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()
            
            sql = "INSERT INTO `"+self.jobtablename+"` (jobId, familyToken, isParent, jobName, userName, vcName, jobType,jobParams ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"
            jobParam = base64.b64encode(json.dumps(jobParams))
            cursor.execute(sql, (jobParams["jobId"], jobParams["familyToken"], jobParams["isParent"], jobParams["jobName"], jobParams["userName"], jobParams["vcName"], jobParams["jobType"],jobParam))
            conn.commit()
            ret = True
        except Exception as e:
            logger.error('AddJob Exception: %s', str(e))
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
        return ret

    @record
    def GetJobList(self, userName, vcName, num = None, status = None, op = ("=","or")):
        ret = []
        conn = None
        cursor = None
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()
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
            fetch_start_time = timeit.default_timer()
            data = cursor.fetchall()
            fetch_elapsed = timeit.default_timer() - fetch_start_time
            logger.info("(fetchall time: %f)", fetch_elapsed)
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
            conn.commit()
        except Exception as e:
            logger.error('GetJobList Exception: %s', str(e))
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
        return ret

    @record
    def GetJobListV2(self, userName, vcName, num = None, status = None, op = ("=","or")):
        ret = {}
        ret["queuedJobs"] = []
        ret["runningJobs"] = []
        ret["finishedJobs"] = []
        ret["visualizationJobs"] = []

        conn = None
        cursor = None
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()

            query = "SELECT {}.jobId, jobName, userName, vcName, jobStatus, jobStatusDetail, jobType, jobTime, jobParams, priority FROM {} left join {} on {}.jobId = {}.jobId where 1".format(self.jobtablename, self.jobtablename, self.jobprioritytablename, self.jobtablename, self.jobprioritytablename)
            if userName != "all":
                query += " and userName = '%s'" % userName

            if vcName != "all":
                query += " and vcName = '%s'" % vcName

            if status is not None:
                if "," not in status:
                    query += " and jobStatus %s '%s'" % (op[0], status)
                else:
                    status_list = [" jobStatus %s '%s' " % (op[0], s) for s in status.split(',')]
                    status_statement = (" "+op[1]+" ").join(status_list)
                    query += " and ( %s ) " % status_statement

            query += " order by jobTime Desc"

            if num is not None:
                query += " limit %s " % str(num)
            cursor.execute(query)

            columns = [column[0] for column in cursor.description]
            data = cursor.fetchall()
            for item in data:
                record = dict(zip(columns, item))
                if record["jobStatusDetail"] is not None:
                    record["jobStatusDetail"] = self.load_json(base64.b64decode(record["jobStatusDetail"]))
                if record["jobParams"] is not None:
                    record["jobParams"] = self.load_json(base64.b64decode(record["jobParams"]))

                if record["jobStatus"] == "running":
                    if record["jobType"] == "training":
                        ret["runningJobs"].append(record)
                    elif record["jobType"] == "visualization":
                        ret["visualizationJobs"].append(record)
                elif record["jobStatus"] == "queued" or record["jobStatus"] == "scheduling" or record["jobStatus"] == "unapproved":
                    ret["queuedJobs"].append(record)
                else:
                    ret["finishedJobs"].append(record)
            conn.commit()
        except Exception as e:
            logger.error('GetJobListV2 Exception: %s', str(e))
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()

        ret["meta"] = {"queuedJobs": len(ret["queuedJobs"]),"runningJobs": len(ret["runningJobs"]),"finishedJobs": len(ret["finishedJobs"]),"visualizationJobs": len(ret["visualizationJobs"])}
        return ret

    @record
    def GetActiveJobList(self):
        ret = []
        conn = None
        cursor = None
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()

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
            conn.commit()
        except Exception as e:
            logger.error('GetActiveJobList Exception: %s', str(e))
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
        return ret

    @record
    def GetJob(self, **kwargs):
        valid_keys = ["jobId", "familyToken", "isParent", "jobName", "userName", "vcName", "jobStatus", "jobType", "jobTime"]
        if len(kwargs) != 1: return []
        key, expected = kwargs.popitem()
        if key not in valid_keys:
            logger.error("DataHandler_GetJob: key is not in valid keys list...")
            return []

        ret = []
        conn = None
        cursor = None
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()

            query = "SELECT `jobId`,`familyToken`,`isParent`,`jobName`,`userName`, `vcName`, `jobStatus`, `jobStatusDetail`, `jobType`, `jobDescriptionPath`, `jobDescription`, `jobTime`, `endpoints`, `jobParams`,`errorMsg` ,`jobMeta`  FROM `%s` where `%s` = '%s' " % (self.jobtablename,key,expected)
            cursor.execute(query)
            columns = [column[0] for column in cursor.description]
            ret = [dict(zip(columns, row)) for row in cursor.fetchall()]
            conn.commit()
        except Exception as e:
            logger.error('GetJob Exception: %s', str(e))
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
        return ret

    @record
    def GetJobV2(self, jobId):
        ret = []
        conn = None
        cursor = None
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()
            query = "SELECT `jobId`, `jobName`, `userName`, `vcName`, `jobStatus`, `jobStatusDetail`, `jobType`, `jobTime`, `jobParams`  FROM `%s` where `jobId` = '%s' " % (self.jobtablename, jobId)
            cursor.execute(query)

            columns = [column[0] for column in cursor.description]
            data = cursor.fetchall()
            for item in data:
                record = dict(zip(columns, item))
                if record["jobStatusDetail"] is not None:
                    record["jobStatusDetail"] = self.load_json(base64.b64decode(record["jobStatusDetail"]))
                if record["jobParams"] is not None:
                    record["jobParams"] = self.load_json(base64.b64decode(record["jobParams"]))
                ret.append(record)
            conn.commit()
        except Exception as e:
            logger.error('GetJobV2 Exception: %s', str(e))
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
        return ret

    @record
    def AddCommand(self, jobId, command):
        ret = False
        conn = None
        cursor = None
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()

            sql = "INSERT INTO `"+self.commandtablename+"` (jobId, command) VALUES (%s,%s)"
            cursor.execute(sql, (jobId, command))
            conn.commit()
            ret = True
        except Exception as e:
            logger.error('AddCommand Exception: %s', str(e))
            ret = False
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
        return ret

    @record
    def GetPendingCommands(self):
        ret = []
        conn = None
        cursor = None
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()
            
            query = "SELECT `id`, `jobId`, `command` FROM `%s` WHERE `status` = 'pending' order by `time`" % (self.commandtablename)
            cursor.execute(query)
        
            for (id, jobId, command) in cursor:
                record = {}
                record["id"] = id
                record["jobId"] = jobId
                record["command"] = command
                ret.append(record)
            conn.commit()
        except Exception as e:
            logger.error('GetPendingCommands Exception: %s', str(e))
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
        return ret

    @record
    def FinishCommand(self, commandId):
        ret = True
        conn = None
        cursor = None
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()
            
            sql = """update `%s` set status = 'run' where `id` = '%s' """ % (self.commandtablename, commandId)
            cursor.execute(sql)
            conn.commit()
            ret = True
        except Exception as e:
            logger.error('FinishCommand Exception: %s', str(e))
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
        return ret

    @record
    def GetCommands(self, jobId):
        ret = []
        conn = None
        cursor = None
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()
            
            query = "SELECT `time`, `command`, `status`, `output` FROM `%s` WHERE `jobId` = '%s' order by `time`" % (self.commandtablename, jobId)
            cursor.execute(query)
            for (time, command, status, output) in cursor:
                record = {}
                record["time"] = time
                record["command"] = command
                record["status"] = status
                record["output"] = output
                ret.append(record)
            conn.commit()
        except Exception as e:
            logger.error('FinishCommand Exception: %s', str(e))
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
        return ret

    def load_json(self, raw_str):
        if raw_str is None:
            return {}
        if isinstance(raw_str, unicode):
            raw_str = str(raw_str)
        try:
            return json.loads(raw_str)
        except:
            return {}

    @record
    def GetPendingEndpoints(self):
        conn = None
        cursor = None
        ret = {}
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()
            query = "SELECT `endpoints` from `%s` where `jobStatus` = '%s' and `endpoints` is not null" % (self.jobtablename, "running")
            cursor.execute(query)
            jobs = cursor.fetchall()
            self.conn.commit()

            # [ {endpoint1:{},endpoint2:{}}, {endpoint3:{}, ... }, ... ]
            endpoints = map(lambda job: self.load_json(job[0]), jobs)
            # {endpoint1: {}, endpoint2: {}, ... }
            # endpoint["status"] == "pending"
            ret = {k: v for d in endpoints for k, v in d.items() if v["status"] == "pending"}
        except Exception as e:
            logger.exception("Query pending endpoints failed!")
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
        return ret

    @record
    def GetJobEndpoints(self, job_id):
        conn = None
        cursor = None
        ret = {}
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()
            query = "SELECT `endpoints` from `%s` where `jobId` = '%s'" % (self.jobtablename, job_id)
            cursor.execute(query)
            jobs = cursor.fetchall()
            self.conn.commit()

            # [ {endpoint1:{},endpoint2:{}}, {endpoint3:{}, ... }, ... ]
            endpoints = map(lambda job: self.load_json(job[0]), jobs)
            # {endpoint1: {}, endpoint2: {}, ... }
            # endpoint["status"] == "pending"
            ret = {k: v for d in endpoints for k, v in d.items()}
        except Exception as e:
            logger.warning("Query job endpoints failed! Job {}".format(job_id), exc_info=True)
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
        return ret

    @record
    def GetDeadEndpoints(self):
        ret = {}
        conn = None
        cursor = None
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()
            # TODO we need job["lastUpdated"] for filtering
            query = "SELECT `endpoints` FROM jobs WHERE `jobStatus` <> 'running' and `jobStatus` <> 'pending' and `jobStatus` <> 'queued' and `jobStatus` <> 'scheduling' order by `jobTime` DESC"
            cursor.execute(query)

            for [endpoints] in cursor:
                endpoint_list = {k: v for k, v in self.load_json(endpoints).items() if v["status"] == "running"}
                ret.update(endpoint_list)
            conn.commit()
        except Exception as e:
            logger.error('Query dead endpoints Exception: %s', str(e))
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
        return ret

    @record
    def UpdateEndpoint(self, endpoint):
        ret = False
        conn = None
        cursor = None
        try:
            job_endpoints = self.GetJobEndpoints(endpoint["jobId"])

            # update jobEndpoints
            job_endpoints[endpoint["id"]] = endpoint

            conn = self.pool.get_connection()
            cursor = conn.cursor()
            
            sql = "UPDATE jobs SET endpoints=%s where jobId=%s"
            cursor.execute(sql, (json.dumps(job_endpoints), endpoint["jobId"]))
            conn.commit()
            ret = True
        except Exception as e:
            logger.exception("Update endpoints failed! Endpoints: {}".format(endpoint))
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
        return ret

    @record
    def GetPendingJobs(self):
        ret = []
        conn = None
        cursor = None
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()
    
            query = "SELECT `jobId`,`jobName`,`userName`, `vcName`, `jobStatus`, `jobStatusDetail`, `jobType`, `jobDescriptionPath`, `jobDescription`, `jobTime`, `endpoints`, `jobParams`,`errorMsg` ,`jobMeta` FROM `%s` where `jobStatus` <> 'error' and `jobStatus` <> 'failed' and `jobStatus` <> 'finished' and `jobStatus` <> 'killed' order by `jobTime` DESC" % (self.jobtablename)
            cursor.execute(query)

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
            conn.commit()
        except Exception as e:
            logger.error('GetPendingJobs Exception: %s', str(e))
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
        return ret

    @record
    def SetJobError(self, jobId, errorMsg):
        ret = False
        conn = None
        cursor = None
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()
    
            sql = """update `%s` set jobStatus = 'error', `errorMsg` = '%s' where `jobId` = '%s' """ % (self.jobtablename, errorMsg, jobId)
            cursor.execute(sql)
            conn.commit()
            ret = True
        except Exception as e:
            logger.error('SetJobError Exception: %s', str(e))
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
        return ret

    @record
    def UpdateJobTextField(self, jobId, field, value):
        ret = False
        conn = None
        cursor = None
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()
    
            sql = "update `%s` set `%s` = '%s' where `jobId` = '%s' " % (self.jobtablename, field, value, jobId)
            cursor.execute(sql)
            conn.commit()
            ret = True
        except Exception as e:
            logger.error('UpdateJobTextField Exception: %s', str(e))
            ret = False
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
        return ret

    @record
    def UpdateJobTextFields(self, conditionFields, dataFields):
        conn = None
        cursor = None
        ret = False
        if not isinstance(conditionFields, dict) or not conditionFields or not isinstance(dataFields, dict) or not dataFields:
            return ret

        try:
            sql = "update `%s` set" % (self.jobtablename) + ",".join([" `%s` = '%s'" % (field, value) for field, value in dataFields.items()]) + " where" + "and".join([" `%s` = '%s'" % (field, value) for field, value in conditionFields.items()])

            conn = self.pool.get_connection()
            cursor = conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            ret = True
        except Exception as e:
            logger.error('updateJobTextFields Exception: %s, ex: %s', fields, str(e))
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
        return ret

    @record
    def GetJobTextField(self, jobId, field):
        ret = None
        conn = None
        cursor = None
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()
            
            query = "SELECT `jobId`, `%s` FROM `%s` where `jobId` = '%s' " % (field, self.jobtablename, jobId)
            cursor.execute(query)
            for (jobId, value) in cursor:
                ret = value
            conn.commit()
        except Exception as e:
            logger.error('GetJobTextField Exception: %s', str(e))
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
        return ret

    @record
    def GetJobTextFields(self, jobId, fields):
        conn = None
        cursor = None
        ret = None
        if not isinstance(fields, list) or not fields:
            return ret

        try:
            sql = "select " + ",".join(fields) + " from " + self.jobtablename + " where jobId='%s'" % (jobId)

            conn = self.pool.get_connection()
            cursor = conn.cursor()
            cursor.execute(sql)

            columns = [column[0] for column in cursor.description]
            for item in cursor.fetchall():
                ret = dict(zip(columns, item))
            self.conn.commit()
        except Exception as e:
            logger.error('GetJobTextFields Exception: %s', str(e))
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
        return ret

    @record
    def AddandGetJobRetries(self, jobId):
        ret = None
        conn = None
        cursor = None
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()

            sql = """update `%s` set `retries` = `retries` + 1 where `jobId` = '%s' """ % (self.jobtablename, jobId)
            cursor.execute(sql)
            conn.commit()
            cursor.close()

            cursor = conn.cursor()
            query = "SELECT `jobId`, `retries` FROM `%s` where `jobId` = '%s' " % (self.jobtablename, jobId)
            cursor.execute(query)

            for (jobId, value) in cursor:
                ret = value
            conn.commit()
        except Exception as e:
            logger.error('AddandGetJobRetries Exception: %s', str(e))
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
        return ret

    @record
    def UpdateClusterStatus(self, clusterStatus):
        ret = False
        conn = None
        cursor = None
        try:
            status = base64.b64encode(json.dumps(clusterStatus))

            conn = self.pool.get_connection()
            cursor = conn.cursor()

            sql = "INSERT INTO `%s` (status) VALUES ('%s')" % (self.clusterstatustablename, status)
            cursor.execute(sql)
            conn.commit()
            ret = True
        except Exception as e:
            logger.error('UpdateClusterStatus Exception: %s', str(e))
            ret = False
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
        return ret

    @record
    def GetClusterStatus(self):
        ret = None
        time = None
        conn = None
        cursor = None
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()

            query = "SELECT `time`, `status` FROM `%s` order by `time` DESC limit 1" % (self.clusterstatustablename)
            cursor.execute(query)
            for (t, value) in cursor:
                ret = json.loads(base64.b64decode(value))
                time = t
            conn.commit()
        except Exception as e:
            logger.error('GetClusterStatus Exception: %s', str(e))
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
        return ret, time


    @record
    def GetUsers(self):
        ret = []
        conn = None
        cursor = None
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()

            query = "SELECT `identityName`,`uid` FROM `%s`" % (self.identitytablename)
            cursor.execute(query)
            for (identityName,uid) in cursor:
                ret.append((identityName,uid))
            conn.commit()
        except Exception as e:
            logger.error('GetUsers Exception: %s', str(e))
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
        return ret


    @record
    def GetActiveJobsCount(self):
        ret = 0
        conn = None
        cursor = None
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()

            query = "SELECT count(ALL id) as c FROM `%s` where `jobStatus` = 'running'" % (self.jobtablename)
            cursor.execute(query)

            for c in cursor:
                ret = c[0]
            conn.commit()
        except Exception as e:
            logger.error('GetActiveJobsCount Exception: %s', str(e))
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
        return ret

    @record
    def GetALLJobsCount(self):
        ret = 0
        conn = None
        cursor = None
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()

            query = "SELECT count(ALL id) as c FROM `%s`" % (self.jobtablename)
            cursor.execute(query)

            for c in cursor:
                ret = c[0]
            conn.commit()
        except Exception as e:
            logger.error('GetALLJobsCount Exception: %s', str(e))
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
        return ret

    @record
    def GetTemplates(self, scope):
        ret = []
        conn = None
        cursor = None
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()

            query = "SELECT `name`, `json` FROM `%s` WHERE `scope` = '%s'" % (self.templatetablename, scope)
            cursor.execute(query)

            for name, json in cursor:
                record = {}
                record["name"] = name
                record["json"] = json
                ret.append(record)
            conn.commit()
        except Exception as e:
            logger.error('GetTemplates Exception: %s', str(e))
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
        return ret

    @record
    def UpdateTemplate(self, name, scope, json):
        ret = False
        conn = None
        cursor = None
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()

            query = "INSERT INTO `" + self.templatetablename + "`(`name`, `scope`, `json`) VALUES(%s, %s, %s) ON DUPLICATE KEY UPDATE `json` = %s"
            cursor.execute(query, (name, scope, json, json))
            conn.commit()
            ret = True
        except Exception as e:
            logger.error('UpdateTemplate Exception: %s', str(e))
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
        return ret

    @record
    def DeleteTemplate(self, name, scope):
        ret = False
        conn = None
        cursor = None
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()

            query = "DELETE FROM `" + self.templatetablename + "` WHERE `name` = %s and `scope` = %s"
            cursor.execute(query, (name, scope))
            conn.commit()
            ret = True
        except Exception as e:
            logger.error('DeleteTemplate Exception: %s', str(e))
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
        return ret

    @record
    def get_job_priority(self):
        ret = {}
        conn = None
        cursor = None
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()

            query = "select jobId, priority from {} where jobId in (select jobId from {} where jobStatus in (\"queued\", \"scheduling\", \"running\", \"unapproved\", \"pausing\", \"paused\"))".format(self.jobprioritytablename, self.jobtablename)
            cursor.execute(query)

            for job_id, priority in cursor:
                ret[job_id] = priority
            conn.commit()
        except Exception as e:
            logger.error('get_job_priority Exception: %s', str(e))
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
        return ret


    @record
    def update_job_priority(self, job_priorites):
        ret = False
        conn = None
        cursor = None
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()

            for job_id, priority in job_priorites.items():
                query = "INSERT INTO {0}(jobId, priority, time) VALUES('{1}', {2}, SYSDATE()) ON DUPLICATE KEY UPDATE jobId='{1}', priority='{2}' ".format(self.jobprioritytablename, job_id, priority)
                cursor.execute(query)
            conn.commit()
            ret = True
        except Exception as e:
            logger.error('update_job_priority Exception: %s', str(e))
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
        return ret

    def __del__(self):
        logger.debug("********************** deleted a DataHandler instance *******************")
        self.Close()

    def Close(self):
        ### !!! This DataHandler uses DB pool, so close connection in each method
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
