#!/usr/bin/env python3

import json
import base64
import logging
import functools
import timeit

import mysql.connector
from prometheus_client import Histogram
from vc_quota import vc_value_str

from config import config, global_vars

logger = logging.getLogger(__name__)

data_handler_fn_histogram = Histogram(
    "datahandler_fn_latency_seconds",
    "latency for executing data handler function (seconds)",
    buckets=(.05, .075, .1, .25, .5, .75, 1.0, 2.5, 5.0, 7.5, 10.0, 12.5, 15.0,
             17.5, 20.0, float("inf")),
    labelnames=("fn_name",))

db_connect_histogram = Histogram("db_connect_latency_seconds",
                                 "latency for connecting to db (seconds)",
                                 buckets=(.05, .075, .1, .25, .5, .75, 1.0, 2.5,
                                          5.0, 7.5, float("inf")))


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


def base64encode(str_val):
    return base64.b64encode(str_val.encode("utf-8")).decode("utf-8")


def base64decode(str_val):
    return base64.b64decode(str_val.encode("utf-8")).decode("utf-8")


class DataHandler(object):
    def __init__(self):
        self.database = "DLWSCluster-%s" % config["clusterId"]
        self.jobtablename = "jobs"
        self.identitytablename = "identity"
        self.acltablename = "acl"
        self.vctablename = "vc"
        self.storagetablename = "storage"
        self.clusterstatustablename = "clusterstatus"
        self.templatetablename = "templates"
        server = config["mysql"]["hostname"]
        username = config["mysql"]["username"]
        password = config["mysql"]["password"]

        self.CreateDatabase()

        with db_connect_histogram.time():
            self.conn = mysql.connector.connect(user=username,
                                                password=password,
                                                host=server,
                                                database=self.database)

        self.CreateTable()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.Close()

    def CreateDatabase(self):
        if "initSQLDB" not in global_vars or not global_vars["initSQLDB"]:
            logger.info("===========init SQL database===============")
            global_vars["initSQLDB"] = True

            server = config["mysql"]["hostname"]
            username = config["mysql"]["username"]
            password = config["mysql"]["password"]

            conn = mysql.connector.connect(user=username,
                                           password=password,
                                           host=server)
            sql = " CREATE DATABASE IF NOT EXISTS `%s` DEFAULT CHARACTER SET 'utf8' " % (
                self.database)
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
                    `jobLogCursor` LONGTEXT  NULL,
                    `retries`             int    NULL DEFAULT 0,
                    `lastUpdated` DATETIME     DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    `priority` INT   DEFAULT 100 NOT NULL,
                    `insight` LONGTEXT  NULL,
                    PRIMARY KEY (`id`),
                    UNIQUE(`jobId`),
                    INDEX (`userName`),
                    INDEX (`vcName`),
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
                    PRIMARY KEY (`id`),
                    INDEX(`time`)
                )
                """ % (self.clusterstatustablename)

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

            sql = """
                CREATE TABLE IF NOT EXISTS  `%s`
                (
                    `id`        INT     NOT NULL AUTO_INCREMENT,
                    `vcName`    varchar(255) NOT NULL UNIQUE,
                    `parent`    varchar(255) DEFAULT NULL,
                    `quota`     varchar(255) NOT NULL,
                    `metadata`  TEXT NOT NULL,
                    `resourceQuota` TEXT NOT NULL,
                    `resourceMetadata`  TEXT NOT NULL,
                    `time`      DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    PRIMARY KEY (`id`),
                    CONSTRAINT `hierarchy` FOREIGN KEY (`parent`) REFERENCES `%s` (`vcName`)
                );
                """ % (self.vctablename, self.vctablename)

            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()

            self.init_vc_sqls(config)

            sql = """
                CREATE TABLE IF NOT EXISTS  `%s`
                (
                    `id`            INT     NOT NULL AUTO_INCREMENT,
                    `identityName`  varchar(255) NOT NULL UNIQUE,
                    `uid`           INT NOT NULL,
                    `gid`           INT NOT NULL,
                    `groups`        MEDIUMTEXT NOT NULL,
                    `public_key`    TEXT NOT NULL,
                    `private_key`   TEXT NOT NULL,
                    `time`          DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    PRIMARY KEY (`id`),
                    UNIQUE(`identityName`)
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

    @record
    def column_exists(self, tablename, columnname):
        sql = "SHOW COLUMNS FROM `{}` LIKE '{}';".format(tablename, columnname)
        cursor = self.conn.cursor()
        cursor.execute(sql)
        result = cursor.fetchone()
        return result is not None

    @record
    def table_exists(self, tablename):
        sql = "SHOW TABLES LIKE '{}'".format(tablename)
        cursor = self.conn.cursor()
        cursor.execute(sql)
        result = cursor.fetchone()
        return result is not None

    @record
    def AddStorage(self, vcName, url, storageType, metadata, defaultMountPath):
        try:
            sql = "INSERT INTO `" + self.storagetablename + "` (storageType, url, metadata, vcName, defaultMountPath) VALUES (%s,%s,%s,%s,%s)"
            cursor = self.conn.cursor()
            cursor.execute(
                sql, (storageType, url, metadata, vcName, defaultMountPath))
            self.conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.exception('AddStorage Exception: %s', str(e))
            return False

    @record
    def DeleteStorage(self, vcName, url):
        try:
            sql = "DELETE FROM `%s` WHERE url = '%s' and vcName = '%s'" % (
                self.storagetablename, url, vcName)
            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.exception('DeleteStorage Exception: %s', str(e))
            return False

    @record
    def ListStorages(self, vcName):
        cursor = self.conn.cursor()
        query = "SELECT `storageType`,`url`,`metadata`,`vcName`,`defaultMountPath` FROM `%s` WHERE vcName = '%s' " % (
            self.storagetablename, vcName)
        ret = []
        try:
            cursor.execute(query)
            for (storageType, url, metadata, vcName,
                 defaultMountPath) in cursor:
                record = {}
                record["vcName"] = vcName
                record["url"] = url
                record["storageType"] = storageType
                record["metadata"] = metadata
                record["defaultMountPath"] = defaultMountPath
                ret.append(record)
        except Exception as e:
            logger.exception('ListStorages Exception: %s', str(e))
            pass
        self.conn.commit()
        cursor.close()
        return ret

    @record
    def UpdateStorage(self, vcName, url, storageType, metadata,
                      defaultMountPath):
        try:
            sql = """update `%s` set storageType = '%s', metadata = '%s', defaultMountPath = '%s' where vcName = '%s' and url = '%s' """ % (
                self.storagetablename, storageType, metadata, defaultMountPath,
                vcName, url)
            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.exception('Exception: %s', str(e))
            return False

    def init_vc_sqls(self, config):
        ratio_dict = {config['defalt_virtual_cluster_name']: 1.0}
        if "vc_resource_ratio" in config:
            ratio_dict = config["vc_resource_ratio"]
        quota, metadata, res_quota, res_meta = vc_value_str(config, ratio_dict)
        if quota == "":
            return

        if len(self.ListVCs()) != 0:
            return

        for vc, vc_res_quota in res_quota.items():
            self.AddVC(vc, quota, metadata, vc_res_quota, res_meta)

    @record
    def AddVC(self, vcName, quota, metadata, res_quota, res_meta):
        try:
            sql = "INSERT INTO `{}` (vcName, quota, metadata, resourceQuota, resourceMetadata) VALUES ('{}', '{}', '{}', '{}', '{}')".format(
                self.vctablename, vcName, quota, metadata, res_quota, res_meta)
            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.exception('AddVC Exception: %s', str(e))
            return False

    @record
    def ListVCs(self):
        cursor = self.conn.cursor()
        query = "SELECT `vcName`,`quota`,`metadata`, `resourceQuota`, `resourceMetadata` FROM `%s`" % self.vctablename
        ret = []
        try:
            cursor.execute(query)
            for vc_name, quota, metadata, resource_quota, resource_metadata in cursor:
                rec = {
                    "vcName": vc_name,
                    "quota": quota,
                    "metadata": metadata,
                    "resourceQuota": resource_quota,
                    "resourceMetadata": resource_metadata
                }
                ret.append(rec)
        except Exception as e:
            logger.exception('Exception: %s', str(e))
            pass
        self.conn.commit()
        cursor.close()
        return ret

    @record
    def DeleteVC(self, vcName):
        try:
            sql = "DELETE FROM `%s` WHERE vcName = '%s'" % (self.vctablename,
                                                            vcName)
            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.exception('DeleteVC Exception: %s', str(e))
            return False

    @record
    def UpdateVC(self, vcName, quota, metadata):
        try:
            sql = """update `%s` set quota = '%s', metadata = '%s' where vcName = '%s' """ % (
                self.vctablename, quota, metadata, vcName)
            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.exception('Exception: %s', str(e))
            return False

    @record
    def GetIdentityInfo(self, identityName):
        cursor = self.conn.cursor()
        query = """SELECT `identityName`,`uid`,`gid`,`groups`,`public_key`,`private_key`
        FROM `%s` WHERE `identityName` = '%s'""" % (self.identitytablename,
                                                    identityName)
        ret = []

        try:
            cursor.execute(query)
            for (identity_name, uid, gid, groups, public_key,
                 private_key) in cursor:
                record = {}
                record["identityName"] = identity_name
                record["uid"] = uid
                record["gid"] = gid
                record["groups"] = json.loads(groups)
                record["public_key"] = public_key
                record["private_key"] = private_key
                ret.append(record)
        except Exception as e:
            logger.exception("failed to get identity of %s", identityName)

        self.conn.commit()
        cursor.close()
        return ret

    @record
    def UpdateIdentityInfo(self, identityName, uid, gid, groups, public_key,
                           private_key):
        try:
            cursor = self.conn.cursor()

            if (isinstance(groups, list)):
                groups = json.dumps(groups)

            sql = """INSERT INTO {0}
            (identityName, uid, gid, groups, public_key, private_key)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            uid=%s, gid=%s, groups=%s""".format(self.identitytablename)

            cursor.execute(sql, (identityName, uid, gid, groups, public_key,
                                 private_key, uid, gid, groups))

            # do not update public_key and private_key if already exist, maybe
            # this key is currently in use
            sql = """UPDATE {0}
            SET public_key = %s, private_key = %s
            WHERE identityName=%s AND public_key="" AND private_key=""
            """.format(self.identitytablename)

            cursor.execute(sql, (public_key, private_key, identityName))
            self.conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.exception('UpdateIdentityInfo Exception %s', identityName)
            return False

    @record
    def UpdateAce(self, identityName, identityId, resource, permissions,
                  isDeny):
        try:
            cursor = self.conn.cursor()
            sql = "insert into {0} (identityName, identityId, resource, permissions, isDeny) values ('{1}', '{2}', '{3}', '{4}', '{5}') on duplicate key update permissions='{4}'".format(
                self.acltablename, identityName, identityId, resource,
                permissions, isDeny)
            cursor.execute(sql)

            self.conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.exception('UpdateAce Exception: %s', str(e))
            return False

    @record
    def UpdateAclIdentityId(self, identityName, identityId):
        try:
            cursor = self.conn.cursor()
            sql = """update `%s` set identityId = '%s' where `identityName` = '%s' """ % (
                self.acltablename, identityId, identityName)
            cursor.execute(sql)

            self.conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.exception('Exception: %s', str(e))
            return False

    @record
    def DeleteResourceAcl(self, resource):
        try:
            cursor = self.conn.cursor()

            sql = "DELETE FROM `%s` WHERE `resource` = '%s'" % (
                self.acltablename, resource)
            cursor.execute(sql)

            self.conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.exception('Exception: %s', str(e))
            return False

    @record
    def DeleteAce(self, identityName, resource):
        try:
            cursor = self.conn.cursor()

            sql = "DELETE FROM `%s` WHERE `identityName` = '%s' and `resource` = '%s'" % (
                self.acltablename, identityName, resource)
            cursor.execute(sql)

            self.conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.exception('DeleteAce Exception: %s', str(e))
            return False

    @record
    def GetAcl(self):
        cursor = self.conn.cursor()
        query = "SELECT `identityName`,`identityId`,`resource`,`permissions`,`isDeny` FROM `%s`" % (
            self.acltablename)
        ret = []
        try:
            cursor.execute(query)
            for (identityName, identityId, resource, permissions,
                 isDeny) in cursor:
                record = {}
                record["identityName"] = identityName
                record["identityId"] = identityId
                record["resource"] = resource
                record["permissions"] = permissions
                record["isDeny"] = isDeny
                ret.append(record)
        except Exception as e:
            logger.exception('Exception: %s', str(e))
            pass
        self.conn.commit()
        cursor.close()
        return ret

    @record
    def GetResourceAcl(self, resource):
        cursor = self.conn.cursor()
        query = "SELECT `identityName`,`identityId`,`resource`,`permissions`,`isDeny` FROM `%s` where `resource` = '%s'" % (
            self.acltablename, resource)
        ret = []
        try:
            cursor.execute(query)
            for (identityName, identityId, resource, permissions,
                 isDeny) in cursor:
                record = {}
                record["identityName"] = identityName
                record["identityId"] = identityId
                record["resource"] = resource
                record["permissions"] = permissions
                record["isDeny"] = isDeny
                ret.append(record)
        except Exception as e:
            logger.exception('Exception: %s', str(e))
        self.conn.commit()
        cursor.close()
        return ret

    @record
    def AddJob(self, jobParams):
        try:
            sql = "INSERT INTO `" + self.jobtablename + "` (jobId, familyToken, isParent, jobName, userName, vcName, jobType,jobParams ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"
            cursor = self.conn.cursor()
            jobParam = base64encode(json.dumps(jobParams))
            cursor.execute(sql, (jobParams["jobId"], jobParams["familyToken"],
                                 jobParams["isParent"], jobParams["jobName"],
                                 jobParams["userName"], jobParams["vcName"],
                                 jobParams["jobType"], jobParam))
            self.conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.exception('Exception: %s', str(e))
            return False

    @record
    def GetJobList(self,
                   userName,
                   vcName,
                   num=None,
                   status=None,
                   op=("=", "or")):
        ret = []
        cursor = self.conn.cursor()
        try:
            query = "SELECT `jobId`,`jobName`,`userName`, `vcName`, `jobStatus`, `jobStatusDetail`, `jobType`, `jobDescriptionPath`, `jobDescription`, `jobTime`, `endpoints`, `jobParams`,`errorMsg` ,`jobMeta`, `lastUpdated` FROM `%s` where 1" % (
                self.jobtablename)
            if userName != "all":
                query += " and `userName` = '%s'" % userName

            if vcName != "all":
                query += " and `vcName` = '%s'" % vcName

            if status is not None:
                if "," not in status:
                    query += " and `jobStatus` %s '%s'" % (op[0], status)
                else:
                    status_list = [
                        " `jobStatus` %s '%s' " % (op[0], s)
                        for s in status.split(',')
                    ]
                    status_statement = (" " + op[1] + " ").join(status_list)
                    query += " and ( %s ) " % status_statement

            query += " order by `jobTime` Desc"

            if num is not None:
                query += " limit %s " % str(num)

            cursor.execute(query)

            data = cursor.fetchall()
            for (jobId, jobName, userName, vcName, jobStatus, jobStatusDetail,
                 jobType, jobDescriptionPath, jobDescription, jobTime,
                 endpoints, jobParams, errorMsg, jobMeta, lastUpdated) in data:
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
                record["lastUpdated"] = lastUpdated
                ret.append(record)
        except Exception as e:
            logger.exception('Exception: %s', str(e))
        self.conn.commit()
        cursor.close()
        return ret

    @record
    def GetJobListV2(self,
                     userName,
                     vcName,
                     num=None,
                     status=None,
                     op=("=", "or")):
        ret = {}
        ret["queuedJobs"] = []
        ret["runningJobs"] = []
        ret["finishedJobs"] = []
        ret["visualizationJobs"] = []

        cursor = None
        try:
            cursor = self.conn.cursor()

            query = "SELECT jobId, jobName, userName, vcName, jobStatus, jobStatusDetail, jobType, jobTime, jobParams, priority FROM %s where 1" % self.jobtablename
            if userName != "all":
                query += " and userName = '%s'" % userName

            if vcName != "all":
                query += " and vcName = '%s'" % vcName

            if status is not None:
                if "," not in status:
                    query += " and jobStatus %s '%s'" % (op[0], status)
                else:
                    status_list = [
                        " jobStatus %s '%s' " % (op[0], s)
                        for s in status.split(',')
                    ]
                    status_statement = (" " + op[1] + " ").join(status_list)
                    query += " and ( %s ) " % status_statement

            query += " order by jobTime Desc"

            if num is not None:
                query += " limit %s " % str(num)

            cursor.execute(query)

            columns = [column[0] for column in cursor.description]
            data = cursor.fetchall()
            for item in data:
                record = dict(list(zip(columns, item)))
                if record["jobStatusDetail"] is not None:
                    record["jobStatusDetail"] = self.load_json(
                        base64decode(record["jobStatusDetail"]))
                if record["jobParams"] is not None:
                    record["jobParams"] = self.load_json(
                        base64decode(record["jobParams"]))

                if record["jobStatus"] == "running":
                    if record["jobType"] == "training":
                        ret["runningJobs"].append(record)
                    elif record["jobType"] == "visualization":
                        ret["visualizationJobs"].append(record)
                elif record["jobStatus"] == "queued" or record[
                        "jobStatus"] == "scheduling" or record[
                            "jobStatus"] == "unapproved":
                    ret["queuedJobs"].append(record)
                else:
                    ret["finishedJobs"].append(record)
            self.conn.commit()
        except Exception as e:
            logger.exception('GetJobListV2 Exception: %s', str(e))
        finally:
            if cursor is not None:
                cursor.close()

        ret["meta"] = {
            "queuedJobs": len(ret["queuedJobs"]),
            "runningJobs": len(ret["runningJobs"]),
            "finishedJobs": len(ret["finishedJobs"]),
            "visualizationJobs": len(ret["visualizationJobs"])
        }
        return ret

    @record
    def get_union_job_list(self, username, vc_name, num, status):
        """Get jobs in status and the latest num jobs that are not in status.

        Args:
            username: Username for jobs
            vc_name: VC name for jobs
            num: Number of the latest jobs that are not in status
            status: Job status

        Returns:
            A list of jobs including all jobs in status and the latest num
            jobs that are not in status.
        """
        ret = []

        if not isinstance(username, str):
            logger.error("username has to be a str")
            return ret

        if not isinstance(vc_name, str):
            logger.error("vc_name has to be a str")
            return ret

        try:
            num = int(num)
        except:
            num = None
        if num is None:
            logger.error("num has to be a number or string of digits")
            return ret

        if isinstance(status, str):
            status = status.split(",")
        elif not isinstance(status, list):
            status = set(status)
        elif not isinstance(status, set):
            logger.error("status has to be a str or a list")
            return ret
        if len(status) == 0:
            logger.error("status must contain at least one item")
            return ret

        cursor = None

        try:
            jobs = self.jobtablename

            cols = [
                "jobId",
                "jobName",
                "userName",
                "vcName",
                "jobStatus",
                "jobStatusDetail",
                "jobType",
                "jobDescriptionPath",
                "jobDescription",
                "jobTime",
                "endpoints",
                "jobParams",
                "errorMsg",
                "jobMeta",
            ]
            query_prefix = "SELECT %s FROM %s WHERE 1" % (
                ",".join(cols),
                jobs,
            )

            if username != "all":
                query_prefix += " AND userName = '%s'" % username

            if vc_name != "all":
                query_prefix += " AND vcName = '%s'" % vc_name

            in_status = ",".join(["'%s'" % e for e in status])

            q_in_status = "%s AND jobStatus IN (%s)" % (
                query_prefix,
                in_status,
            )
            q_in_status += " ORDER BY jobTime DESC"
            q_not_in_status = "%s AND jobStatus NOT IN (%s)" % (
                query_prefix,
                in_status,
            )
            q_not_in_status += " ORDER BY jobTime DESC LIMIT %s" % num
            query = "(%s) UNION (%s)" % (q_in_status, q_not_in_status)

            cursor = self.conn.cursor()
            cursor.execute(query)

            columns = [column[0] for column in cursor.description]
            data = cursor.fetchall()
            for item in data:
                rec = dict(list(zip(columns, item)))
                ret.append(rec)

            self.conn.commit()
        except:
            logger.exception("Exception in getting union job list. status %s",
                             status,
                             exc_info=True)
        finally:
            if cursor is not None:
                cursor.close()

        cursor.close()
        return ret

    @record
    def get_union_job_list_v2(self, username, vc_name, num, status):
        """Get jobs in status and the latest num jobs that are not in status.

        Args:
            username: Username for jobs
            vc_name: VC name for jobs
            num: Number of the latest jobs that are not in status
            status: Job status

        Returns:
            A list of jobs including all jobs in status and the latest num
            jobs that are not in status.
        """
        ret = {
            "queuedJobs": [],
            "runningJobs": [],
            "finishedJobs": [],
            "visualizationJobs": [],
            "meta": {
                "queuedJobs": 0,
                "runningJobs": 0,
                "finishedJobs": 0,
                "visualizationJobs": 0,
            }
        }

        if not isinstance(username, str):
            logger.error("username has to be a str")
            return ret

        if not isinstance(vc_name, str):
            logger.error("vc_name has to be a str")
            return ret

        try:
            num = int(num)
        except:
            num = None
        if num is None:
            logger.error("num has to be a number or string of digits")
            return ret

        if isinstance(status, str):
            status = status.split(",")
        elif not isinstance(status, list):
            status = set(status)
        elif not isinstance(status, set):
            logger.error("status has to be a str or a list")
            return ret
        if len(status) == 0:
            logger.error("status must contain at least one item")
            return ret

        cursor = None
        queued_jobs = []
        running_jobs = []
        finished_jobs = []
        visualization_jobs = []
        try:
            jobs = self.jobtablename

            cols = [
                "jobId",
                "jobName",
                "userName",
                "vcName",
                "jobStatus",
                "jobStatusDetail",
                "jobType",
                "jobTime",
                "jobParams",
                "priority",
            ]
            query_prefix = "SELECT %s FROM %s WHERE 1" % (",".join(cols), jobs)

            if username != "all":
                query_prefix += " AND userName = '%s'" % username

            if vc_name != "all":
                query_prefix += " AND vcName = '%s'" % vc_name

            in_status = ",".join(["'%s'" % e for e in status])

            q_in_status = "%s AND jobStatus IN (%s)" % (
                query_prefix,
                in_status,
            )
            q_in_status += " ORDER BY jobTime DESC"
            q_not_in_status = "%s AND jobStatus NOT IN (%s)" % (
                query_prefix,
                in_status,
            )
            q_not_in_status += " ORDER BY jobTime DESC LIMIT %s" % num
            query = "(%s) UNION (%s)" % (q_in_status, q_not_in_status)

            cursor = self.conn.cursor()
            cursor.execute(query)

            columns = [column[0] for column in cursor.description]
            data = cursor.fetchall()
            for item in data:
                rec = dict(list(zip(columns, item)))
                j_detail = rec["jobStatusDetail"]
                j_params = rec["jobParams"]
                j_status = rec["jobStatus"]
                j_type = rec["jobType"]

                if j_detail is not None:
                    rec["jobStatusDetail"] = self.load_json(
                        base64decode(j_detail))

                if j_params is not None:
                    rec["jobParams"] = self.load_json(base64decode(j_params))

                if j_status == "running":
                    if j_type == "training":
                        running_jobs.append(rec)
                    elif j_type == "visualization":
                        visualization_jobs.append(rec)
                elif j_status in ["unapproved", "queued", "scheduling"]:
                    queued_jobs.append(rec)
                else:
                    finished_jobs.append(rec)

            self.conn.commit()
        except:
            logger.exception("Exception in getting union job list. status %s",
                             status,
                             exc_info=True)
        finally:
            if cursor is not None:
                cursor.close()

        ret["queuedJobs"] = queued_jobs
        ret["runningJobs"] = running_jobs
        ret["finishedJobs"] = finished_jobs
        ret["visualizationJobs"] = visualization_jobs
        ret["meta"]["queuedJobs"] = len(queued_jobs)
        ret["meta"]["runningJobs"] = len(running_jobs)
        ret["meta"]["finishedJobs"] = len(finished_jobs)
        ret["meta"]["visualizationJobs"] = len(visualization_jobs)

        return ret

    @record
    def GetActiveJobList(self):
        ret = []
        cursor = self.conn.cursor()
        try:
            query = "SELECT `jobId`, `userName`, `vcName`, `jobParams`, `jobStatus` FROM `%s` WHERE `jobStatus` = 'scheduling' OR `jobStatus` = 'running'" % (
                self.jobtablename)

            cursor.execute(query)
            data = cursor.fetchall()

            for (jobId, userName, vcName, jobParams, jobStatus) in data:
                record = {}
                record["jobId"] = jobId
                record["userName"] = userName
                record["vcName"] = vcName
                record["jobParams"] = jobParams
                record["jobStatus"] = jobStatus
                ret.append(record)
        except Exception as e:
            logger.exception('GetActiveJobList Exception: %s', str(e))
        self.conn.commit()
        cursor.close()
        return ret

    @record
    def GetJob(self, **kwargs):
        valid_keys = [
            "jobId", "familyToken", "isParent", "jobName", "userName", "vcName",
            "jobStatus", "jobType", "jobTime"
        ]
        if len(kwargs) != 1:
            return []
        key, expected = kwargs.popitem()
        if key not in valid_keys:
            logger.error("DataHandler_GetJob: key is not in valid keys list...")
            return []
        cursor = self.conn.cursor()
        query = "SELECT `jobId`,`familyToken`,`isParent`,`jobName`,`userName`, `vcName`, `jobStatus`, `jobStatusDetail`, `jobType`, `jobDescriptionPath`, `jobDescription`, `jobTime`, `endpoints`, `jobParams`,`errorMsg` ,`jobMeta`  FROM `%s` where `%s` = '%s' " % (
            self.jobtablename, key, expected)
        cursor.execute(query)
        columns = [column[0] for column in cursor.description]
        ret = [dict(list(zip(columns, row))) for row in cursor.fetchall()]
        self.conn.commit()
        cursor.close()
        return ret

    @record
    def GetJobV2(self, jobId):
        ret = []
        cursor = None
        try:
            cursor = self.conn.cursor()
            query = "SELECT `jobId`, `jobName`, `userName`, `vcName`, `jobStatus`, `jobStatusDetail`, `jobType`, `jobTime`, `jobParams`, `insight` FROM `%s` where `jobId` = '%s' " % (
                self.jobtablename, jobId)
            cursor.execute(query)

            columns = [column[0] for column in cursor.description]
            data = cursor.fetchall()
            for item in data:
                record = dict(list(zip(columns, item)))
                if record["jobStatusDetail"] is not None:
                    record["jobStatusDetail"] = self.load_json(
                        base64decode(record["jobStatusDetail"]))
                if record["jobParams"] is not None:
                    record["jobParams"] = self.load_json(
                        base64decode(record["jobParams"]))
                if record["insight"] is not None:
                    record["insight"] = self.load_json(
                        base64decode(record["insight"]))
                ret.append(record)
            self.conn.commit()
        except Exception as e:
            logger.exception('GetJobV2 Exception: %s', str(e))
        finally:
            if cursor is not None:
                cursor.close()
        return ret

    def load_json(self, raw_str):
        if raw_str is None:
            return {}
        if isinstance(raw_str, str):
            raw_str = str(raw_str)
        try:
            return json.loads(raw_str)
        except:
            return {}

    @record
    def GetPendingEndpoints(self):
        cursor = None
        pendings = {}
        runnings = {}
        try:
            cursor = self.conn.cursor()
            query = "SELECT `endpoints` from `%s` where `jobStatus` = '%s' and `endpoints` is not null" % (
                self.jobtablename, "running")
            cursor.execute(query)
            jobs = cursor.fetchall()
            self.conn.commit()

            # [ {endpoint1:{},endpoint2:{}}, {endpoint3:{}, ... }, ... ]
            endpoints = [self.load_json(job[0]) for job in jobs]
            # {endpoint1: {}, endpoint2: {}, ... }
            # endpoint["status"] == "pending"
            pendings = {
                k: v for d in endpoints
                for k, v in list(d.items())
                if v["status"] == "pending"
            }
            runnings = {
                k: v for d in endpoints
                for k, v in list(d.items())
                if v["status"] == "running"
            }
        except Exception as e:
            logger.exception("Query pending endpoints failed!")
        finally:
            if cursor is not None:
                cursor.close()
        return pendings, runnings

    @record
    def GetJobEndpoints(self, job_id):
        cursor = None
        ret = {}
        try:
            cursor = self.conn.cursor()
            query = "SELECT `endpoints` from `%s` where `jobId` = '%s'" % (
                self.jobtablename, job_id)
            cursor.execute(query)
            jobs = cursor.fetchall()
            self.conn.commit()

            # [ {endpoint1:{},endpoint2:{}}, {endpoint3:{}, ... }, ... ]
            endpoints = [self.load_json(job[0]) for job in jobs]
            # {endpoint1: {}, endpoint2: {}, ... }
            # endpoint["status"] == "pending"
            ret = {k: v for d in endpoints for k, v in list(d.items())}
        except Exception as e:
            logger.warning("Query job endpoints failed! Job {}".format(job_id),
                           exc_info=True)
        finally:
            if cursor is not None:
                cursor.close()
        return ret

    @record
    def GetDeadEndpoints(self):
        try:
            cursor = self.conn.cursor()
            # TODO we need job["lastUpdated"] for filtering
            query = "SELECT `endpoints` FROM jobs WHERE `jobStatus` <> 'running' and `jobStatus` <> 'pending' and `jobStatus` <> 'queued' and `jobStatus` <> 'scheduling'"
            cursor.execute(query)
            dead_endpoints = {}
            for [endpoints] in cursor:
                endpoint_list = {
                    k: v
                    for k, v in list(self.load_json(endpoints).items())
                    if v["status"] == "running"
                }
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
            job_endpoints = self.GetJobEndpoints(endpoint["jobId"])

            # update jobEndpoints
            job_endpoints[endpoint["id"]] = endpoint

            sql = "UPDATE jobs SET endpoints=%s where jobId=%s"
            cursor = self.conn.cursor()
            cursor.execute(sql, (json.dumps(job_endpoints), endpoint["jobId"]))
            self.conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.exception(
                "Update endpoints failed! Endpoints: {}".format(endpoint))
            return False

    @record
    def GetPendingJobs(self):
        cursor = self.conn.cursor()
        query = "SELECT `jobId`,`jobName`,`userName`, `vcName`, `jobStatus`, `jobStatusDetail`, `jobType`, `jobDescriptionPath`, `jobDescription`, `jobTime`, `endpoints`, `jobParams`,`errorMsg` ,`jobMeta` FROM `%s` where `jobStatus` <> 'error' and `jobStatus` <> 'failed' and `jobStatus` <> 'finished' and `jobStatus` <> 'killed' order by `jobTime` DESC" % (
            self.jobtablename)
        cursor.execute(query)
        ret = []
        for (jobId, jobName, userName, vcName, jobStatus, jobStatusDetail,
             jobType, jobDescriptionPath, jobDescription, jobTime, endpoints,
             jobParams, errorMsg, jobMeta) in cursor:
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
        return self.UpdateJobTextFields({"jobId": jobId},
                                        {"errorMsg": errorMsg})

    @record
    def UpdateJobTextFields(self, conditionFields, dataFields):
        cursor = None
        ret = False
        if not isinstance(conditionFields,
                          dict) or not conditionFields or not isinstance(
                              dataFields, dict) or not dataFields:
            return ret

        sql_template = ["UPDATE", "`%s`" % (self.jobtablename), "SET"]

        set_stmt = []
        set_values = []
        for field, value in dataFields.items():
            set_stmt.append("`%s`=%s" % (field, "%s"))
            set_values.append(value)

        where_stmt = []
        where_values = []
        for field, value in conditionFields.items():
            where_stmt.append("`%s`=%s" % (field, "%s"))
            where_values.append(value)

        sql_template.append(",".join(set_stmt))
        sql_template.append("WHERE")
        sql_template.append(" AND ".join(where_stmt))

        sql = " ".join(sql_template)
        values = []
        values.extend(set_values)
        values.extend(where_values)
        logger.debug("sql is %s, values is %s", sql, values)

        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, values)
            self.conn.commit()
            ret = True
        except Exception as e:
            logger.exception(
                'failed to UpdateJobTextFields conditions %s, data %s',
                conditionFields, dataFields)
        finally:
            if cursor is not None:
                cursor.close()
        return ret

    @record
    def GetJobTextField(self, jobId, field):
        cursor = self.conn.cursor()
        query = "SELECT `jobId`, `%s` FROM `%s` where `jobId` = '%s' " % (
            field, self.jobtablename, jobId)
        ret = None
        try:
            cursor.execute(query)
            for (jobId, value) in cursor:
                ret = value
        except Exception as e:
            logger.exception('Exception: %s', str(e))
            pass
        self.conn.commit()
        cursor.close()
        return ret

    @record
    def GetJobTextFields(self, jobId, fields):
        cursor = None
        ret = None
        if not isinstance(fields, list) or not fields:
            return ret

        try:
            sql = "select " + ",".join(
                fields) + " from " + self.jobtablename + " where jobId='%s'" % (
                    jobId)

            cursor = self.conn.cursor()
            cursor.execute(sql)

            columns = [column[0] for column in cursor.description]
            for item in cursor.fetchall():
                ret = dict(list(zip(columns, item)))
            self.conn.commit()
        except Exception as e:
            logger.exception('GetJobTextFields Exception: %s', str(e))
        finally:
            if cursor is not None:
                cursor.close()
        return ret

    @record
    def AddandGetJobRetries(self, jobId):
        sql = """update `%s` set `retries` = `retries` + 1 where `jobId` = '%s' """ % (
            self.jobtablename, jobId)
        cursor = self.conn.cursor()
        cursor.execute(sql)
        self.conn.commit()
        cursor.close()

        cursor = self.conn.cursor()
        query = "SELECT `jobId`, `retries` FROM `%s` where `jobId` = '%s' " % (
            self.jobtablename, jobId)
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
            status = base64encode(
                json.dumps(clusterStatus, separators=(",", ":")))

            sql = "INSERT INTO `%s` (status) VALUES ('%s')" % (
                self.clusterstatustablename, status)
            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.exception('Exception: %s', str(e))
            return False

    @record
    def GetClusterStatus(self):
        cursor = self.conn.cursor()
        query = "SELECT `time`, `status` FROM `%s` order by `time` DESC limit 1" % (
            self.clusterstatustablename)
        ret = None
        time = None
        try:
            cursor.execute(query)
            for (t, value) in cursor:
                ret = json.loads(base64decode(value))
                time = t
        except Exception as e:
            logger.exception('GetClusterStatus Exception: %s', str(e))
        self.conn.commit()
        cursor.close()
        return ret, time

    @record
    def GetUsers(self):
        cursor = self.conn.cursor()
        query = "SELECT `identityName`,`uid`,`public_key`,`private_key` FROM `%s`" % (
            self.identitytablename)
        ret = []
        try:
            cursor.execute(query)
            for (identityName, uid, public_key, private_key) in cursor:
                ret.append((identityName, uid, public_key, private_key))
        except Exception as e:
            logger.exception('Exception: %s', str(e))
        self.conn.commit()
        cursor.close()
        return ret

    @record
    def GetActiveJobsCount(self):
        cursor = self.conn.cursor()
        query = "SELECT count(ALL id) as c FROM `%s` where `jobStatus` = 'running'" % (
            self.jobtablename)
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
        query = "SELECT `name`, `json` FROM `%s` WHERE `scope` = '%s'" % (
            self.templatetablename, scope)
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
            logger.exception('Exception: %s', str(e))
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
            logger.exception('Exception: %s', str(e))
            return False

    @record
    def get_job_priority(self):
        cursor = self.conn.cursor()
        query = "select jobId, priority from %s where jobStatus in (\"queued\", \"scheduling\", \"running\", \"unapproved\", \"pausing\", \"paused\")" % self.jobtablename
        cursor.execute(query)
        priority_dict = {}
        for job_id, priority in cursor:
            priority_dict[job_id] = priority
        self.conn.commit()
        cursor.close()

        return priority_dict

    @record
    def update_job_priority(self, job_priorites):
        cases = " ".join([
            "WHEN '%s' THEN %i" % (jobId, priority)
            for jobId, priority in list(job_priorites.items())
        ])
        jobIds = ",".join(
            ["'%s'" % jobId for jobId in list(job_priorites.keys())])
        query = "update {0} set priority = CASE jobId {1} END WHERE jobId in ({2})".format(
            self.jobtablename, cases, jobIds)
        cursor = self.conn.cursor()
        cursor.execute(query)
        self.conn.commit()
        cursor.close()
        return True

    @record
    def get_fields_for_jobs(self, job_ids, fields):
        cursor = None
        ret = []

        if job_ids is None or not isinstance(job_ids, list):
            logger.error("job_ids has to be a list. job_ids: %s", job_ids)
            return ret
        if len(job_ids) == 0:
            logger.error("job_ids is an empty list")
            return ret

        if fields is None or not isinstance(fields, list):
            logger.error("fields has to be a list. fields: %s", fields)
            return ret
        if len(fields) == 0:
            logger.error("fields is an empty list")
            return ret

        try:
            sql_cols = ",".join(fields)
            sql_job_ids = ",".join(["'%s'" % job_id for job_id in job_ids])
            sql = "SELECT %s FROM %s WHERE jobId IN (%s)" % (
                sql_cols, self.jobtablename, sql_job_ids)

            cursor = self.conn.cursor()
            cursor.execute(sql)

            cols = [col[0] for col in cursor.description]
            for item in cursor.fetchall():
                ret.append(dict(zip(cols, item)))
            self.conn.commit()
        except Exception:
            logger.exception("Exception in getting fields %s for jobs %s",
                             fields,
                             job_ids,
                             exc_info=True)
        finally:
            if cursor is not None:
                cursor.close()
        return ret

    @record
    def update_text_fields_for_jobs(self, job_ids, fields):
        cursor = None
        ret = False

        if job_ids is None or not isinstance(job_ids, list):
            logger.error("job_ids has to be a list. job_ids: %s", job_ids)
            return ret
        if len(job_ids) == 0:
            logger.error("job_ids is an empty list")
            return ret

        if fields is None or not isinstance(fields, dict):
            logger.error("fields has to be a dict. fields: %s", fields)
            return ret
        if len(fields) == 0:
            logger.error("fields is an empty dict")
            return ret
        for k, v in fields.items():
            if not isinstance(v, str):
                logger.error("fields can only contain str value. %s: %s", k, v)
                return ret

        try:
            sql_col_vals = ",".join(
                [" %s = '%s'" % (k, v) for k, v in fields.items()])
            sql_job_ids = ",".join(["'%s'" % job_id for job_id in job_ids])
            sql = "UPDATE %s SET %s WHERE jobId IN (%s)" % (
                self.jobtablename, sql_col_vals, sql_job_ids)

            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            ret = True
        except Exception:
            logger.exception("Exception in updating fields %s for jobs %s",
                             fields,
                             job_ids,
                             exc_info=True)
        finally:
            if cursor is not None:
                cursor.close()
        return ret

    @record
    def count_rows(self, table):
        cursor = None
        ret = None
        try:
            query = "SELECT COUNT(*) AS num_rows FROM %s" % table
            cursor = self.conn.cursor()
            cursor.execute(query)

            for num_rows in cursor:
                ret = num_rows[0]
                break

            self.conn.commit()
        except:
            logger.exception("Exception in counting rows for table %s", table)
        finally:
            if cursor is not None:
                cursor.close()
        return ret

    def delete_rows_from_table_older_than_days(self,
                                               table,
                                               days_ago,
                                               col="time",
                                               cond=None):
        cursor = None
        ret = False
        try:
            query = "DELETE FROM %s WHERE %s < NOW() - INTERVAL %s DAY" % \
                    (table, col, days_ago)
            if isinstance(cond, dict):
                for field, op_and_value in cond.items():
                    op, value = op_and_value
                    if isinstance(value, list):
                        value = "(%s)" % ",".join(["'%s'" % v for v in value])
                    query += " AND `%s` %s %s" % (field, op, value)

            cursor = self.conn.cursor()
            cursor.execute(query)
            self.conn.commit()
            ret = True
        except:
            logger.exception(
                "Exception in deleting rows older than %s in col %s "
                "for table %s", days_ago, col, table)
        finally:
            if cursor is not None:
                cursor.close()
        return ret

    def __del__(self):
        logger.debug(
            "********************** deleted a DataHandler instance *******************"
        )
        self.Close()

    def Close(self):
        ### !!! DataHandler is not threadsafe object, a same object cannot be used in multiple threads
        try:
            self.conn.close()
        except Exception as e:
            pass


if __name__ == '__main__':
    pass
