# from config import config
import pyodbc
import json
from config import config
from config import global_vars
import base64

from MyLogger import MyLogger



class DataHandler:
    def __init__(self):
        self.logger = MyLogger()
        self.CreateDatabase()
        self.logger.debug ("********************** created a new Data Handler *******************")
        self.server = config["database"]["hostname"] 
        self.database = "DLWorkspaceCluster-%s" % config["clusterId"]
        self.username = config["database"]["username"]
        self.password = config["database"]["password"]
        # self.driver = '/usr/lib/x86_64-linux-gnu/libodbc.so'
        self.driver = '{ODBC Driver 13 for SQL Server}'
        self.connstr = 'DRIVER='+self.driver+';PORT=1433;SERVER='+self.server+';PORT=1433;DATABASE='+self.database+';UID='+self.username+';PWD='+self.password
        #print "Try to connect with string: " + self.connstr
        self.conn = pyodbc.connect(self.connstr)
        self.connected = True
        #print "Connecting to server ..."
        self.jobtablename = "jobs-%s" %  config["clusterId"]
        self.usertablename = "users-%s" %  config["clusterId"]
        self.clusterstatustablename = "clusterstatus-%s" %  config["clusterId"]
        self.commandtablename = "commands-%s" %  config["clusterId"]

        self.CreateTable()




    def CreateDatabase(self):
        if "initSQLDB" not in global_vars or not global_vars["initSQLDB"]:
            self.logger.info("===========init SQL database===============")
            global_vars["initSQLDB"] = True
            server = config["database"]["hostname"] 
            username = config["database"]["username"]
            password = config["database"]["password"]
            database = "DLWorkspaceCluster-%s" % config["clusterId"]

            driver = '{ODBC Driver 13 for SQL Server}'
            connstr = 'DRIVER='+driver+';PORT=1433;SERVER='+server+';PORT=1433;UID='+username+';PWD='+password
            conn = pyodbc.connect(connstr,autocommit=True)
            sql = "if not exists (SELECT name FROM dbo.sysdatabases WHERE name = '%s') CREATE DATABASE [%s];" % (database, database)
            cursor = conn.cursor()
            cursor.execute(sql)
            cursor.close()
            conn.close()

    def CreateTable(self):
        if "initSQLTable" not in global_vars or not global_vars["initSQLTable"]:
            self.logger.info( "===========init SQL Tables ===============")
            global_vars["initSQLTable"] = True
            sql = """
            if not exists (select * from sysobjects where name='%s' and xtype='U')
                BEGIN
                CREATE TABLE [dbo].[%s]
                (
                    [id]        INT          IDENTITY (1, 1) NOT NULL,
                    [jobId] varchar(50)   NOT NULL,
                    [familyToken] varchar(50)   NOT NULL,
                    [isParent] INT   NOT NULL,
                    [jobName]         varchar(max) NOT NULL,
                    [userName]         varchar(255) NOT NULL,
                    [jobStatus]         varchar(255) NOT NULL DEFAULT 'unapproved',
                    [jobStatusDetail] varchar(max) NULL, 
                    [jobType]         varchar(max) NOT NULL,
                    [jobDescriptionPath]  NTEXT NULL,
                    [jobDescription]  NTEXT NULL,
                    [jobTime] DATETIME     DEFAULT (getdate()) NOT NULL,
                    [endpoints] NTEXT NULL, 
                    [errorMsg] NTEXT NULL, 
                    [jobParams] NTEXT NOT NULL, 
                    [jobMeta] NTEXT NULL, 
                    [jobLog] NTEXT NULL, 
                    [retries]             int    NULL DEFAULT 0,
                    PRIMARY KEY CLUSTERED ([id] ASC)
                );
                CREATE INDEX jobusernameindex ON [dbo].[%s] ([userName]);
                CREATE INDEX jobtimeindex ON [dbo].[%s] ([jobTime]);
                CREATE INDEX jobIdindex ON [dbo].[%s] ([jobId]);
                CREATE INDEX jobStatusindex ON [dbo].[%s] ([jobStatus]);
                END
                """ % (self.jobtablename,self.jobtablename,self.jobtablename,self.jobtablename,self.jobtablename,self.jobtablename)

            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()


            sql = """
            if not exists (select * from sysobjects where name='%s' and xtype='U')
                CREATE TABLE [dbo].[%s]
                (
                    [id]        INT          IDENTITY (1, 1) NOT NULL,
                    [status]         NTEXT NOT NULL,
                    [time] DATETIME     DEFAULT (getdate()) NOT NULL,
                    PRIMARY KEY CLUSTERED ([id] ASC)
                )
                """ % (self.clusterstatustablename,self.clusterstatustablename)

            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()


            sql = """
            if not exists (select * from sysobjects where name='%s' and xtype='U')
                CREATE TABLE [dbo].[%s]
                (
                    [id]        INT          IDENTITY (1, 1) NOT NULL,
                    [jobId] varchar(50)   NOT NULL,
                    [status]         varchar(255) NOT NULL DEFAULT 'pending',
                    [time] DATETIME     DEFAULT (getdate()) NOT NULL,
                    [command] NTEXT NOT NULL, 
                    [output] NTEXT NULL, 
                    PRIMARY KEY CLUSTERED ([id] ASC)
                )
                """ % (self.commandtablename,self.commandtablename)

            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()


            sql = """
            if not exists (select * from sysobjects where name='%s' and xtype='U')
                CREATE TABLE [dbo].[%s]
                (
                    [id]        INT          IDENTITY (1, 1) NOT NULL,
                    [username]         varchar(255) NOT NULL,
                    [userId]         varchar(255) NOT NULL,
                    [time] DATETIME     DEFAULT (getdate()) NOT NULL,
                    PRIMARY KEY CLUSTERED ([id] ASC)
                )
                """ % (self.usertablename,self.usertablename)

            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()


    def AddJob(self, jobParams):
        try:
            sql = """INSERT INTO [%s] (jobId, familyToken, isParent, jobName, userName, jobType,jobParams ) VALUES (?,?,?,?,?,?,?)""" % self.jobtablename
            cursor = self.conn.cursor()
            jobParam = base64.b64encode(json.dumps(jobParams))
            cursor.execute(sql, jobParams["jobId"], jobParams["familyToken"], jobParams["isParent"], jobParams["jobName"], jobParams["userName"], jobParams["jobType"],jobParam)
            self.conn.commit()
            cursor.close()
            return True
        except:
            return False


    def GetJobList(self, userName):
        ret = []
        cursor = self.conn.cursor()
        try:
            query = "SELECT [jobId],[jobName],[userName], [jobStatus], [jobStatusDetail], [jobType], [jobDescriptionPath], [jobDescription], [jobTime], [endpoints], [jobParams],[errorMsg] ,[jobMeta] FROM [%s]" % self.jobtablename
            if userName != "all":
                query += " where [userName] = '%s'" % userName
            else:
                query += " where [jobStatus] <> 'error' and [jobStatus] <> 'failed' and [jobStatus] <> 'finished' and [jobStatus] <> 'killed'"
            query += " order by [jobTime] Desc"
            cursor.execute(query)
            for (jobId,jobName,userName, jobStatus,jobStatusDetail, jobType, jobDescriptionPath, jobDescription, jobTime, endpoints, jobParams,errorMsg, jobMeta) in cursor:
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
        except:
            pass                
        cursor.close()
        return ret


    def GetJob(self, **kwargs):
        valid_keys = ["jobId", "familyToken", "isParent", "jobName", "userName", "jobStatus", "jobType", "jobTime"]
        if len(kwargs) != 1: return []
        key, expected = kwargs.popitem()
        if key not in valid_keys: 
            self.logger.error("DataHandler_GetJob: key is not in valid keys list...")
            return []
        cursor = self.conn.cursor()
        query = "SELECT [jobId],[familyToken],[isParent],[jobName],[userName], [jobStatus], [jobStatusDetail], [jobType], [jobDescriptionPath], [jobDescription], [jobTime], [endpoints], [jobParams],[errorMsg] ,[jobMeta]  FROM [%s] where [%s] = '%s' " % (self.jobtablename,key,expected)
        cursor.execute(query)
        columns = [column[0] for column in cursor.description]
        ret = [dict(zip(columns, row)) for row in cursor.fetchall()]
        cursor.close()
        return ret


    def AddCommand(self,jobId,command):
        try:
            sql = """INSERT INTO [%s] (jobId, command) VALUES (?,?)""" % self.commandtablename
            cursor = self.conn.cursor()
            cursor.execute(sql, jobId, command)
            self.conn.commit()
            cursor.close()
            return True
        except:
            return False


    def GetPendingCommands(self):
        cursor = self.conn.cursor()
        query = "SELECT [id], [jobId], [command] FROM [%s] WHERE [status] = 'pending' order by [time]" % (self.commandtablename)
        cursor.execute(query)
        ret = []
        for (id, jobId, command) in cursor:
            record = {}
            record["id"] = id
            record["jobId"] = jobId
            record["command"] = command
            ret.append(record)
        cursor.close()

        return ret    


    def FinishCommand(self,commandId):
        try:
            sql = """update [%s] set status = 'run' where [id] = '%s' """ % (self.commandtablename, commandId)
            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()
            return True
        except:
            return False


    def GetCommands(self, jobId):
        cursor = self.conn.cursor()
        query = "SELECT [time], [command], [status], [output] FROM [%s] WHERE [jobId] = '%s' order by [time]" % (self.commandtablename, jobId)
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

        return ret    


    def KillJob(self,jobId):
        try:
            sql = """update [%s] set jobStatus = 'killing' where [jobId] = '%s' """ % (self.jobtablename,jobId)
            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()
            return True
        except:
            return False


    def ApproveJob(self,jobId):
        try:
            sql = """update [%s] set jobStatus = 'queued' where [jobId] = '%s' """ % (self.jobtablename,jobId)
            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()
            return True
        except:
            return False


    def GetPendingJobs(self):
        cursor = self.conn.cursor()
        query = "SELECT [jobId],[jobName],[userName], [jobStatus], [jobType], [jobDescriptionPath], [jobDescription], [jobTime], [endpoints], [jobParams],[errorMsg] ,[jobMeta] FROM [%s] where [jobStatus] <> 'error' and [jobStatus] <> 'failed' and [jobStatus] <> 'finished' and [jobStatus] <> 'killed' order by [jobTime] DESC" % (self.jobtablename)
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

        return ret        


    def SetJobError(self,jobId,errorMsg):
        try:
            sql = """update [%s] set jobStatus = 'error', [errorMsg] = ? where [jobId] = '%s' """ % (self.jobtablename,jobId)
            cursor = self.conn.cursor()
            cursor.execute(sql,errorMsg)
            self.conn.commit()
            cursor.close()
            return True
        except:
            return False        


    def UpdateJobTextField(self,jobId,field,value):
        try:
            sql = """update [%s] set [%s] = ? where [jobId] = '%s' """ % (self.jobtablename,field, jobId)
            cursor = self.conn.cursor()
            cursor.execute(sql,value)
            self.conn.commit()
            cursor.close()
            return True
        except:
            return False


    def GetJobTextField(self,jobId,field):
        cursor = self.conn.cursor()
        query = "SELECT [jobId], [%s] FROM [%s] where [jobId] = '%s' " % (field, self.jobtablename,jobId)
        ret = None
        try:
            cursor.execute(query)
            for (jobId, value) in cursor:
                ret = value
        except:
            pass
        cursor.close()
        return ret

    def AddandGetJobRetries(self,jobId):

        sql = """update [%s] set [retries] = [retries] + 1 where [jobId] = '%s' """ % (self.jobtablename, jobId)
        cursor = self.conn.cursor()
        cursor.execute(sql)
        self.conn.commit()
        cursor.close()

        cursor = self.conn.cursor()
        query = "SELECT [jobId], [retries] FROM [%s] where [jobId] = '%s' " % (self.jobtablename,jobId)
        cursor.execute(query)
        ret = None

        for (jobId, value) in cursor:
            ret = value
        cursor.close()

        return ret


    def UpdateClusterStatus(self,clusterStatus):
        try:

            sql = """INSERT INTO [%s] (status) VALUES (?)""" % self.clusterstatustablename
            cursor = self.conn.cursor()
            status = base64.b64encode(json.dumps(clusterStatus))
            cursor.execute(sql,status)
            self.conn.commit()
            cursor.close()
            return True
        except:
            return False


    def GetClusterStatus(self):
        cursor = self.conn.cursor()
        query = "SELECT TOP 1 [time], [status] FROM [%s] order by [time] DESC" % (self.clusterstatustablename)
        ret = None
        time = None
        try:
            cursor.execute(query)
            for (t, value) in cursor:
                ret = json.loads(base64.b64decode(value))
                time = t
        except Exception as e:
            print e
            pass
        cursor.close()
        return ret, time

    def GetUsersCount(self, username):
        cursor = self.conn.cursor()
        query = "SELECT count(ALL id) as c FROM [%s] where [username] = '%s' " % (self.usertablename,username)
        cursor.execute(query)
        ret = 0
        for c in cursor:
            ret = c[0]
        cursor.close()

        return ret        
    
    def AddUser(self, username,userId):
        try:
            if self.GetUsersCount(username) == 0:
                sql = """INSERT INTO [%s] (username,userId) VALUES (?,?)""" % self.usertablename
                cursor = self.conn.cursor()
                cursor.execute(sql, username,userId)
                self.conn.commit()
                cursor.close()
            return True
        except:
            return False

    def GetUsers(self):
        cursor = self.conn.cursor()
        query = "SELECT [username],[userId] FROM [%s]" % (self.usertablename)
        ret = []
        try:
            cursor.execute(query)
            for (username,userId) in cursor:
                ret.append((username,userId))
        except Exception as e:
            print e
            pass
        cursor.close()
        return ret




    def GetActiveJobsCount(self):
        cursor = self.conn.cursor()
        query = "SELECT count(ALL id) as c FROM [%s] where [jobStatus] <> 'error' and [jobStatus] <> 'failed' and [jobStatus] <> 'finished' and [jobStatus] <> 'killed' " % (self.jobtablename)
        cursor.execute(query)
        ret = 0
        for c in cursor:
            ret = c[0]
        cursor.close()

        return ret        

    def GetALLJobsCount(self):
        cursor = self.conn.cursor()
        query = "SELECT count(ALL id) as c FROM [%s]" % (self.jobtablename)
        cursor.execute(query)
        ret = 0
        for c in cursor:
            ret = c[0]
        cursor.close()

        return ret    

    def __del__(self):
        self.logger.debug("********************** deleted a DataHandler instance *******************")
        self.Close()

    def Close(self):
        if (self.connected):
            self.connected = False
            self.conn.close()

if __name__ == '__main__':
    TEST_INSERT_JOB = False
    TEST_QUERY_JOB_LIST = False
    CREATE_TABLE = False
    CREATE_DB = True
    dataHandler = DataHandler()
    
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