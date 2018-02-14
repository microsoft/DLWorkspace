# from config import config
import mysql.connector
import json
import base64
import os

import timeit

from Queue import Queue
import threading

from config import config
from config import global_vars
from MyLogger import MyLogger

logger = MyLogger()


class DataHandler:
    def __init__(self):
        start_time = timeit.default_timer()
        
        self.CreateDatabase()
        server = config["mysql"]["hostname"] 
        database = "DLWorkspaceCluster-%s" % config["clusterId"]
        username = config["mysql"]["username"]
        password = config["mysql"]["password"]
        self.conn = mysql.connector.connect(user=username, password=password,
                                      host=server,database=database)

        logger.debug ("Get database connection %s" % str(self.conn))

        #print "Connecting to server ..."
        self.jobtablename = "jobs"
        self.usertablename = "users"
        self.clusterstatustablename = "clusterstatus"
        self.commandtablename = "commands"

        self.CreateTable()
        elapsed = timeit.default_timer() - start_time
        logger.debug ("DataHandler initialization, time elapsed %f s" % elapsed)



    def CreateDatabase(self):
        if "initSQLDB" not in global_vars or not global_vars["initSQLDB"]:
            logger.info("===========init SQL database===============")
            global_vars["initSQLDB"] = True

            server = config["mysql"]["hostname"] 
            database = "DLWorkspaceCluster-%s" % config["clusterId"]
            username = config["mysql"]["username"]
            password = config["mysql"]["password"]

            conn = mysql.connector.connect(user=username, password=password,
                                          host=server)            
            sql = " CREATE DATABASE IF NOT EXISTS `%s` DEFAULT CHARACTER SET 'utf8' " % (database)
            cursor = conn.cursor()
            cursor.execute(sql)
            conn.commit()
            cursor.close()
            conn.close()

    def CreateTable(self):
        if "initSQLTable" not in global_vars or not global_vars["initSQLTable"]:
            logger.info( "===========init SQL Tables ===============")
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
                    PRIMARY KEY (`id`),
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
                    `status`         TEXT NOT NULL,
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
                    `id`        INT     NOT NULL AUTO_INCREMENT,
                    `username`         varchar(255) NOT NULL,
                    `userId`         varchar(255) NOT NULL,
                    `time` DATETIME     DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    PRIMARY KEY (`id`)
                )
                """ % (self.usertablename)

            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()


    def AddJob(self, jobParams):
        try:
            start_time = timeit.default_timer()
            sql = "INSERT INTO `"+self.jobtablename+"` (jobId, familyToken, isParent, jobName, userName, jobType,jobParams ) VALUES (%s,%s,%s,%s,%s,%s,%s)"
            cursor = self.conn.cursor()
            jobParam = base64.b64encode(json.dumps(jobParams))
            cursor.execute(sql, (jobParams["jobId"], jobParams["familyToken"], jobParams["isParent"], jobParams["jobName"], jobParams["userName"], jobParams["jobType"],jobParam))
            self.conn.commit()
            cursor.close()
            elapsed = timeit.default_timer() - start_time
            logger.info ("DataHandler: added job %s to database, time elapsed %f s" % (jobParams["jobId"],elapsed))
            return True
        except Exception, e:
           logger.error('Exception: '+ str(e))
           return False


    def GetJobList(self, userName, num = None, status = None, op = ("=","or")):
        start_time = timeit.default_timer()
        ret = []
        cursor = self.conn.cursor()
        try:
            query = "SELECT `jobId`,`jobName`,`userName`, `jobStatus`, `jobStatusDetail`, `jobType`, `jobDescriptionPath`, `jobDescription`, `jobTime`, `endpoints`, `jobParams`,`errorMsg` ,`jobMeta` FROM `%s`" % (self.jobtablename)
            if userName != "all":
                query += " where `userName` = '%s'" % userName
            else:
                query += " where `id` > -1 "
            if status is not None:
                if "," not in status:
                    query += " and `jobStatus` %s '%s'" % (op[0],status)
                else:
                    status_list = [ " `jobStatus` %s '%s' " % (op[0],s) for s in status.split(',')]
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
            for (jobId,jobName,userName, jobStatus,jobStatusDetail, jobType, jobDescriptionPath, jobDescription, jobTime, endpoints, jobParams,errorMsg, jobMeta) in data:
                record = {}
                record["jobId"] = jobId
                record["jobName"] = jobName
                record["userName"] = userName
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
        except Exception, e:
            logger.error('Exception: '+ str(e))
            pass                
        cursor.close()
        elapsed = timeit.default_timer() - start_time
        logger.info ("DataHandler: get job list for user %s , time elapsed %f s (SQL query time: %f)" % (userName, elapsed, elapsed1))
        return ret


    def GetJob(self, **kwargs):
        start_time = timeit.default_timer()
        valid_keys = ["jobId", "familyToken", "isParent", "jobName", "userName", "jobStatus", "jobType", "jobTime"]
        if len(kwargs) != 1: return []
        key, expected = kwargs.popitem()
        if key not in valid_keys: 
            logger.error("DataHandler_GetJob: key is not in valid keys list...")
            return []
        cursor = self.conn.cursor()
        query = "SELECT `jobId`,`familyToken`,`isParent`,`jobName`,`userName`, `jobStatus`, `jobStatusDetail`, `jobType`, `jobDescriptionPath`, `jobDescription`, `jobTime`, `endpoints`, `jobParams`,`errorMsg` ,`jobMeta`  FROM `%s` where `%s` = '%s' " % (self.jobtablename,key,expected)
        cursor.execute(query)
        columns = [column[0] for column in cursor.description]
        ret = [dict(zip(columns, row)) for row in cursor.fetchall()]
        cursor.close()
        elapsed = timeit.default_timer() - start_time
        logger.info ("DataHandler: get job details with query %s=%s , time elapsed %f s" % (key, expected, elapsed))
        return ret


    def AddCommand(self,jobId,command):
        try:
            start_time = timeit.default_timer()
            sql = "INSERT INTO `"+self.jobtablename+"` (jobId, command) VALUES (%s,%s)" 
            cursor = self.conn.cursor()
            cursor.execute(sql, (jobId, command))
            self.conn.commit()
            cursor.close()
            elapsed = timeit.default_timer() - start_time
            logger.info ("DataHandler: add command to database, jobId: %s , time elapsed %f s" % (jobId, elapsed))
            return True
        except Exception, e:
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
        cursor.close()
        elapsed = timeit.default_timer() - start_time
        logger.info ("DataHandler: get pending command , time elapsed %f s" % (elapsed))
        return ret    


    def FinishCommand(self,commandId):
        try:
            start_time = timeit.default_timer()
            sql = """update `%s` set status = 'run' where `id` = '%s' """ % (self.commandtablename, commandId)
            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()
            elapsed = timeit.default_timer() - start_time
            logger.info ("DataHandler: set command %s as finished , time elapsed %f s" % (commandId, elapsed))
            return True
        except Exception, e:
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
        cursor.close()
        elapsed = timeit.default_timer() - start_time
        logger.info ("DataHandler: get command list for job %s , time elapsed %f s" % (jobId, elapsed))
        return ret    


    def KillJob(self,jobId):
        try:
            start_time = timeit.default_timer()
            sql = """update `%s` set jobStatus = 'killing' where `jobId` = '%s' """ % (self.jobtablename,jobId)
            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()
            elapsed = timeit.default_timer() - start_time
            logger.info ("DataHandler: mark job %s to be killed in database, time elapsed %f s" % (jobId, elapsed))
            return True
        except Exception, e:
            logger.error('Exception: '+ str(e))
            return False


    def ApproveJob(self,jobId):
        try:
            start_time = timeit.default_timer()
            sql = """update `%s` set jobStatus = 'queued' where `jobId` = '%s' """ % (self.jobtablename,jobId)
            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()
            elapsed = timeit.default_timer() - start_time
            logger.info ("DataHandler: approved job %s , time elapsed %f s" % (jobId, elapsed))
            return True
        except Exception, e:
            logger.error('Exception: '+ str(e))
            return False


    def GetPendingJobs(self):
        start_time = timeit.default_timer()
        cursor = self.conn.cursor()
        query = "SELECT `jobId`,`jobName`,`userName`, `jobStatus`, `jobType`, `jobDescriptionPath`, `jobDescription`, `jobTime`, `endpoints`, `jobParams`,`errorMsg` ,`jobMeta` FROM `%s` where `jobStatus` <> 'error' and `jobStatus` <> 'failed' and `jobStatus` <> 'finished' and `jobStatus` <> 'killed' order by `jobTime` DESC" % (self.jobtablename)
        cursor.execute(query)
        ret = []
        for (jobId,jobName,userName, jobStatus, jobType, jobDescriptionPath, jobDescription, jobTime, endpoints, jobParams,errorMsg, jobMeta) in cursor:
            record = {}
            record["jobId"] = jobId
            record["jobName"] = jobName
            record["userName"] = userName
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
        cursor.close()
        elapsed = timeit.default_timer() - start_time
        logger.info ("DataHandler: get pending jobs , time elapsed %f s" % (elapsed))
        return ret        


    def SetJobError(self,jobId,errorMsg):
        try:
            start_time = timeit.default_timer()
            sql = """update `%s` set jobStatus = 'error', `errorMsg` = '%s' where `jobId` = '%s' """ % (self.jobtablename,errorMsg,jobId)
            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()
            elapsed = timeit.default_timer() - start_time
            logger.info ("DataHandler: set job %s error status in database, time elapsed %f s" % (jobId, elapsed))
            return True
        except Exception, e:
            logger.error('Exception: '+ str(e))
            return False        


    def UpdateJobTextField(self,jobId,field,value):
        try:
            start_time = timeit.default_timer()
            sql = "update `%s` set `%s` = '%s' where `jobId` = '%s' " % (self.jobtablename,field,value,jobId)
            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()
            elapsed = timeit.default_timer() - start_time
            logger.info ("DataHandler: update job %s, field %s , time elapsed %f s" % (jobId, field, elapsed))
            return True
        except Exception, e:
            logger.error('Exception: '+ str(e))
            return False


    def GetJobTextField(self,jobId,field):
        start_time = timeit.default_timer()
        cursor = self.conn.cursor()
        query = "SELECT `jobId`, `%s` FROM `%s` where `jobId` = '%s' " % (field, self.jobtablename,jobId)
        ret = None
        try:
            cursor.execute(query)
            for (jobId, value) in cursor:
                ret = value
        except Exception, e:
            logger.error('Exception: '+ str(e))
            pass
        cursor.close()
        elapsed = timeit.default_timer() - start_time
        logger.info ("DataHandler: get filed %s of job %s , time elapsed %f s" % (field, jobId, elapsed))
        return ret

    def AddandGetJobRetries(self,jobId):
        start_time = timeit.default_timer()
        sql = """update `%s` set `retries` = `retries` + 1 where `jobId` = '%s' """ % (self.jobtablename, jobId)
        cursor = self.conn.cursor()
        cursor.execute(sql)
        self.conn.commit()
        cursor.close()

        cursor = self.conn.cursor()
        query = "SELECT `jobId`, `retries` FROM `%s` where `jobId` = '%s' " % (self.jobtablename,jobId)
        cursor.execute(query)
        ret = None

        for (jobId, value) in cursor:
            ret = value
        cursor.close()
        elapsed = timeit.default_timer() - start_time
        logger.info ("DataHandler: get and update retries for job %s , time elapsed %f s" % (jobId, elapsed))
        return ret


    def UpdateClusterStatus(self,clusterStatus):
        try:
            status = base64.b64encode(json.dumps(clusterStatus))
            
            start_time = timeit.default_timer()
            sql = "INSERT INTO `%s` (status) VALUES ('%s')" % (self.clusterstatustablename,status)
            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()
            elapsed = timeit.default_timer() - start_time
            logger.info ("DataHandler: update cluster status, time elapsed %f s" % (elapsed))
            return True
        except Exception, e:
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
        except Exception, e:
            logger.error('Exception: '+ str(e))
            pass
        cursor.close()
        elapsed = timeit.default_timer() - start_time
        logger.info ("DataHandler: get cluster status , time elapsed %f s" % (elapsed))
        return ret, time

    def GetUsersCount(self, username):
        start_time = timeit.default_timer()
        cursor = self.conn.cursor()
        query = "SELECT count(ALL id) as c FROM `%s` where `userName` = '%s' " % (self.usertablename,username)
        cursor.execute(query)
        ret = 0
        for c in cursor:
            ret = c[0]
        cursor.close()
        elapsed = timeit.default_timer() - start_time
        logger.info ("DataHandler: get user count, time elapsed %f s" % ( elapsed))
        return ret        
    
    def AddUser(self, username,userId):
        try:
            start_time = timeit.default_timer()
            if self.GetUsersCount(username) == 0:
                sql = "INSERT INTO `"+self.usertablename+"` (username,userId) VALUES (%s,%s)"
                cursor = self.conn.cursor()
                cursor.execute(sql, (username,userId))
                self.conn.commit()
                cursor.close()
            elapsed = timeit.default_timer() - start_time
            logger.info ("DataHandler: add user %s to database , time elapsed %f s" % (username, elapsed))
            return True
        except Exception, e:
            logger.error('Exception: '+ str(e))
            return False

    def GetUsers(self):
        start_time = timeit.default_timer()
        cursor = self.conn.cursor()
        query = "SELECT `userName`,`userId` FROM `%s`" % (self.usertablename)
        ret = []
        try:
            cursor.execute(query)
            for (username,userId) in cursor:
                ret.append((username,userId))
        except Exception, e:
            logger.error('Exception: '+ str(e))
            pass
        cursor.close()
        elapsed = timeit.default_timer() - start_time
        logger.info ("DataHandler: get users, time elapsed %f s" % ( elapsed))
        return ret




    def GetActiveJobsCount(self):
        cursor = self.conn.cursor()
        query = "SELECT count(ALL id) as c FROM `%s` where `jobStatus` <> 'error' and `jobStatus` <> 'failed' and `jobStatus` <> 'finished' and `jobStatus` <> 'killed' " % (self.jobtablename)
        cursor.execute(query)
        ret = 0
        for c in cursor:
            ret = c[0]
        cursor.close()

        return ret        

    def GetALLJobsCount(self):
        cursor = self.conn.cursor()
        query = "SELECT count(ALL id) as c FROM `%s`" % (self.jobtablename)
        cursor.execute(query)
        ret = 0
        for c in cursor:
            ret = c[0]
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
    print dataHandler.GetJobList("hongzl@microsoft.com", num = 1)
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
