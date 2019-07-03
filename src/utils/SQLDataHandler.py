# from config import config
import pyodbc
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

### set to a larger number if flask is running on multithreading
sql_max_connect_num = 35
sql_live_connect_num = 25


class SQLConnManager:

    @staticmethod
    def Connect():
        server = config["database"]["hostname"] 
        database = "DLWSCluster-%s" % config["clusterId"]
        username = config["database"]["username"]
        password = config["database"]["password"]
        # self.driver = '/usr/lib/x86_64-linux-gnu/libodbc.so'
        driver = '{ODBC Driver 13 for SQL Server}'
        connstr = 'DRIVER='+driver+';PORT=1433;SERVER='+server+';PORT=1433;DATABASE='+database+';UID='+username+';PWD='+password
        #print "Try to connect with string: " + connstr
        conn = pyodbc.connect(connstr)
        return conn

    @staticmethod
    def TestSQLConnection(conn):
        connected = False
        try:
            c = conn.cursor()
            sql = "select top 1 id from sysobjects"
            c.execute(sql)
            c.close()
            connected = True
        except Exception as e:
            logger.error ("Exception: %s" % str(e) )
            connected = False
        return connected
    @staticmethod
    def GetConnection():
        conn = None

        acquired = global_vars["sql_lock"].acquire()
        try:
            if global_vars["sql_connections"].qsize() > 0:
                logger.debug("current connection pool size %d" %(global_vars["sql_connections"].qsize()))
                try:
                    conn = global_vars["sql_connections"].get(block = False)
                except Exception as e:
                    logger.error ("Exception: %s" % str(e) )
                if conn is not None:
                    logger.debug("Get a database connection from connection pool, current pool size %d: connection Id: %s" %(global_vars["sql_connections"].qsize(), str(conn)))                    

        except Exception as e:
            logger.error ("Exception: %s" % str(e) )
        finally:
            if acquired:
                global_vars["sql_lock"].release()


        ### try to wait for 1s, other threads may release the connection
        if conn is None and global_vars["sql_connection_num"] > 0:
            try:
                conn = global_vars["sql_connections"].get(timeout = 1)
            except Exception as e:
                pass

        if conn is not None:
            # check the connection is still alive
            connected = SQLConnManager.TestSQLConnection(conn)

            if not connected:
                logger.debug ("An existing database connection in the connection pool has been disconnected by remote server, recreate a new connection. we have %d live connections" % global_vars["sql_connection_num"] )
                try:
                    conn.close()
                except:
                    pass
                conn = SQLConnManager.Connect()

        if conn is None and global_vars["sql_connection_num"] <= sql_max_connect_num:
            conn = SQLConnManager.Connect()
            acquired = global_vars["sql_lock"].acquire()
            try:
                global_vars["sql_connection_num"] += 1
            except Exception as e:
                logger.error ("Exception: %s" % str(e) )
            finally:
                if acquired:
                    global_vars["sql_lock"].release()
            logger.debug ("Created a new SQL database connection in pid (%s), we have %d live connections" % (os.getpid(),global_vars["sql_connection_num"]) )


        if conn is None:
            logger.warn ("%d live connections currently are in the system, this request will be blocked" % global_vars["sql_connection_num"] )
            global_vars["sql_connections"].get(block = True)
            logger.warn ("%d live connections currently are in the system, the blocked request has been released" % global_vars["sql_connection_num"] )
        return conn

    @staticmethod
    def ReturnConnection(conn):
        if conn is not None:
            connected = SQLConnManager.TestSQLConnection(conn)
            acquired = global_vars["sql_lock"].acquire()
            returnedConn = False
            try:
                if connected:
                    if global_vars["sql_connection_num"] <= sql_live_connect_num:
                        #maxsize=0 in the queue, put won't be blocked
                        global_vars["sql_connections"].put(conn)
                        returnedConn = True
                    else:
                        conn.close()
                        logger.debug ("Closed a SQL database connection, we have %d live connections" % global_vars["sql_connection_num"] )
                else:
                    logger.debug ("An existing database connection in the connection pool has been disconnected by remote server. we have %d live connections" % (global_vars["sql_connection_num"] - 1 ))
                    try:
                        conn.close()
                    except:
                        pass
            except Exception as e:
                    logger.error ("Exception: %s" % str(e) )
            finally:
                if not returnedConn:
                    global_vars["sql_connection_num"] -= 1
                    try:
                        conn.close()
                    except:
                        pass
                if acquired:
                    global_vars["sql_lock"].release()
        return None

class DataHandler:
    def __init__(self):
        start_time = timeit.default_timer()
        self.CreateDatabase()

        logger.debug ("********************** created a new Data Handler *******************")
        self.conn = SQLConnManager.GetConnection()
        logger.debug ("Get database connection %s" % str(self.conn))
        
        #print "Connecting to server ..."
        self.jobtablename = "jobs-%s" %  config["clusterId"]
        self.acltablename = "acl-%s" %  config["clusterId"]
        self.identitytablename = "identity-%s" %  config["clusterId"]
        self.vctablename = "vc-%s" %  config["clusterId"]
        self.storagetablename = "storage-%s" %  config["clusterId"]
        self.clusterstatustablename = "clusterstatus-%s" %  config["clusterId"]
        self.commandtablename = "commands-%s" %  config["clusterId"]

        self.CreateTable()
        elapsed = timeit.default_timer() - start_time
        logger.debug ("DataHandler initialization, time elapsed %f s" % elapsed)



    def CreateDatabase(self):
        if "initSQLDB" not in global_vars or not global_vars["initSQLDB"]:
            logger.info("===========init SQL database===============")
            global_vars["initSQLDB"] = True
            server = config["database"]["hostname"] 
            username = config["database"]["username"]
            password = config["database"]["password"]
            database = "DLWSCluster-%s" % config["clusterId"]

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
            logger.info( "===========init SQL Tables ===============")
            global_vars["initSQLTable"] = True
            sql = """
            if not exists (select * from sysobjects where name='%s' and xtype='U')
                BEGIN
                CREATE TABLE [dbo].[%s]
                (
                    [id]        INT          IDENTITY (1, 1) NOT NULL,
                    [jobId] varchar(50)   NOT NULL UNIQUE,
                    [familyToken] varchar(50)   NOT NULL,
                    [isParent] INT   NOT NULL,
                    [jobName]         varchar(max) NOT NULL,
                    [userName]         varchar(255) NOT NULL,
                    [vcName]         varchar(255) NOT NULL,
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
                    PRIMARY KEY NONCLUSTERED  ([id] ASC),
                    INDEX jobusernameindex CLUSTERED ([userName]),
                    INDEX jobtimeindex NONCLUSTERED  ([jobTime]),
                    INDEX jobIdindex NONCLUSTERED  ([jobId]),
                    INDEX jobStatusindex NONCLUSTERED  ([jobStatus])
                );
                END
                """ % (self.jobtablename,self.jobtablename)

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
                    [id]                INT          IDENTITY (1, 1) NOT NULL,
                    [storageType]       varchar(255) NOT NULL,
                    [url]               varchar(255) NOT NULL,
                    [metadata]          varchar(max) NOT NULL,
                    [vcName]            varchar(255) NOT NULL,
                    [defaultMountPath]  varchar(255) NOT NULL,
                    [time]              DATETIME DEFAULT (getdate()) NOT NULL,
                    PRIMARY KEY CLUSTERED ([id] ASC),
                    CONSTRAINT vc_url UNIQUE (vcName,url),
                    CONSTRAINT vc_mountPath UNIQUE (vcName,defaultMountPath)
                )
                """ % (self.storagetablename,self.storagetablename)

            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()


            sql = """
            if not exists (select * from sysobjects where name='%s' and xtype='U')
                CREATE TABLE [dbo].[%s]
                (
                    [id]         INT          IDENTITY (1, 1) NOT NULL,
                    [vcName]     varchar(255) NOT NULL UNIQUE,
                    [parent]     varchar(255) DEFAULT NULL,
                    [quota]      varchar(255) NOT NULL,
                    [metadata]   varchar(max) NOT NULL,
                    [time]       DATETIME     DEFAULT (getdate()) NOT NULL,
                    PRIMARY KEY CLUSTERED ([id] ASC),
                    FOREIGN KEY(parent) REFERENCES [dbo].[%s](vcName),
                )
                """ % (self.vctablename,self.vctablename, self.vctablename)

            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()


            sql = """
            if not exists (select * from sysobjects where name='%s' and xtype='U')
                CREATE TABLE [dbo].[%s]
                (
                    [id]            INT          IDENTITY (1, 1) NOT NULL,
                    [identityName]  varchar(255) NOT NULL UNIQUE,
                    [uid]           INT NOT NULL,
                    [gid]           INT NOT NULL,
                    [groups]        varchar(max) NOT NULL,
                    [time]          DATETIME     DEFAULT (getdate()) NOT NULL,
                    PRIMARY KEY CLUSTERED ([id] ASC)
                )
                """ % (self.identitytablename,self.identitytablename)

            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()

            
            sql = """
            if not exists (select * from sysobjects where name='%s' and xtype='U')
                CREATE TABLE [dbo].[%s]
                (
                    [id]            INT          IDENTITY (1, 1) NOT NULL,
                    [identityName]  varchar(255) NOT NULL,
                    [identityId]    INT NOT NULL,
                    [resource]      varchar(255) NOT NULL,
                    [permissions]   INT  NOT NULL,
                    [isDeny]        INT  NOT NULL,
                    [time]          DATETIME     DEFAULT (getdate()) NOT NULL,
                    PRIMARY KEY CLUSTERED ([id] ASC),
                    CONSTRAINT identityName_resource UNIQUE (identityName,resource)
                )
                """ % (self.acltablename,self.acltablename)

            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()


    def AddStorage(self, vcName, url, storageType, metadata, defaultMountPath):
        try:
            start_time = timeit.default_timer()
            sql = "INSERT INTO [%s] (storageType, url, metadata, vcName, defaultMountPath) VALUES (?,?,?,?,?)""" % self.storagetablename
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
            sql = "DELETE FROM [%s] WHERE [url] = '%s' and [vcName] = '%s'" % (self.storagetablename, url, vcName)
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
        query = "SELECT [vcName],[url],[storageType],[metadata],[defaultMountPath] FROM [%s] WHERE [vcName] = '%s' " % (self.storagetablename, vcName)
        ret = []
        try:
            cursor.execute(query)
            for (vcName,url,storageType,metadata,defaultMountPath) in cursor:
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
            sql = """update [%s] set storageType = '%s', metadata = '%s', defaultMountPath = '%s' where [vcName] = '%s' and [url] = '%s' """ % (self.storagetablename, storageType, metadata, defaultMountPath, vcName, url)
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
            sql = """INSERT INTO [%s] (vcName, quota, metadata) VALUES (?,?,?)""" % self.vctablename
            cursor = self.conn.cursor()
            cursor.execute(sql, vcName, quota, metadata)
            self.conn.commit()
            cursor.close()
            elapsed = timeit.default_timer() - start_time
            logger.info ("DataHandler: AddVC to DB: vcName: %s , time elapsed %f s" % (vcName, elapsed))
            return True
        except Exception as e:
            logger.error('Exception: '+ str(e))
            return False


    def ListVCs(self, vcName):
        start_time = timeit.default_timer()
        cursor = self.conn.cursor()
        query = "SELECT [vcName],[quota],[metadata] FROM [%s]" % (self.vctablename)
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
        logger.info ("DataHandler: ListVCs time elapsed %f s" % ( elapsed))
        return ret   


    def DeleteVC(self, vcName):
        try:
            start_time = timeit.default_timer()
            sql = "DELETE FROM [%s] WHERE [vcName] = '%s'" % (self.vctablename, vcName)
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
            sql = """update [%s] set quota = '%s', metadata = '%s'  where [vcName] = '%s'""" % (self.vctablename, quota, metadata, vcName)
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
        query = "SELECT [identityName],[uid],[gid],[groups] FROM [%s] where [identityName] = '%s'" % (self.identitytablename, identityName)
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
            logger.error('Exception: '+ str(e))
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
            
            if len(self.GetIdentityInfo(identityName)) == 0:
                sql = """INSERT INTO [%s] (identityName,uid,gid,groups) VALUES (?,?,?,?)""" % self.identitytablename
                cursor.execute(sql, identityName, uid, gid, json.dumps(groups))
            else:
                sql = """update [%s] set uid = '%s', gid = '%s', groups = '%s' where [identityName] = '%s' """ % (self.identitytablename, uid, gid, groups, identityName)
                cursor.execute(sql)
            
            self.conn.commit()
            cursor.close()
            elapsed = timeit.default_timer() - start_time
            logger.info ("DataHandler: UpdateIdentityInfo %s to database , time elapsed %f s" % (identityName, elapsed))
            return True
        except Exception as e:
            logger.error('Exception: '+ str(e))
            return False


    def GetAceCount(self, identityId, resource):
        start_time = timeit.default_timer()
        cursor = self.conn.cursor()
        query = "SELECT count(ALL id) as c FROM [%s] where [identityId] = '%s' and [resource] = '%s'" % (self.acltablename,identityId, resource)
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
          
            if self.GetAceCount(identityId, resource) == 0:
                sql = """INSERT INTO [%s] (identityName,identityId,resource,permissions,isDeny) VALUES (?,?,?,?,?)""" % self.acltablename
                cursor.execute(sql, identityName, identityId, resource, permissions, isDeny)
            else:
                sql = """update [%s] set permissions = '%s' where [identityName] = '%s' and [resource] = '%s' """ % (self.acltablename, permissions, identityName, resource)
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
            sql = """update [%s] set identityName = '%s' where [identityName] = '%s' """ % (self.acltablename, identityId, identityName)
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
        
            sql = "DELETE FROM [%s] WHERE [resource] = '%s'" % (self.acltablename, resource)
            cursor = self.conn.cursor()
            
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
        
            sql = "DELETE FROM [%s] WHERE [identityName] = '%s' and [resource] = '%s'" % (self.acltablename, identityName, resource)
            cursor = self.conn.cursor()
            
            self.conn.commit()
            cursor.close()
            elapsed = timeit.default_timer() - start_time
            logger.info ("DataHandler: DeleteAce %s : %s, time elapsed %f s" % (resource, identityName, elapsed))
            return True
        except Exception as e:
            logger.error('Exception: '+ str(e))
            return False


    def GetAcl(self):
        start_time = timeit.default_timer()
        cursor = self.conn.cursor()
        query = "SELECT [identityName],[identityId],[resource],[permissions],[isDeny] FROM [%s]" % (self.acltablename)
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
        query = "SELECT [identityName],[identityId],[resource],[permissions],[isDeny] FROM [%s] where [resource] = '%s'" % (self.acltablename, resource)
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
            sql = """INSERT INTO [%s] (jobId, familyToken, isParent, jobName, userName, vcName, jobType,jobParams ) VALUES (?,?,?,?,?,?,?)""" % self.jobtablename
            cursor = self.conn.cursor()
            jobParam = base64.b64encode(json.dumps(jobParams))
            cursor.execute(sql, jobParams["jobId"], jobParams["familyToken"], jobParams["isParent"], jobParams["jobName"], jobParams["userName"], jobParams["vcName"], jobParams["jobType"],jobParam)
            self.conn.commit()
            cursor.close()
            elapsed = timeit.default_timer() - start_time
            logger.info ("DataHandler: added job %s to database, time elapsed %f s" % (jobParams["jobId"],elapsed))
            return True
        except Exception as e:
           logger.error('Exception: '+ str(e))
           return False


    def GetJobList(self, userName, vcName, num = None, status = None, op = ("=","or")):
        start_time = timeit.default_timer()
        ret = []
        cursor = self.conn.cursor()
        try:
            if num is None:
                selectNum = ""
            else:
                selectNum = " TOP %s " % str(num)
            query = "SELECT %s [jobId],[jobName],[userName], [vcName], [jobStatus], [jobStatusDetail], [jobType], [jobDescriptionPath], [jobDescription], [jobTime], [endpoints], [jobParams],[errorMsg] ,[jobMeta] FROM [%s] where [vcName] = '%s'" % (selectNum, self.jobtablename, vcName)
            if userName != "all":
                query += " and [userName] = '%s'" % userName
            if status is not None:
                if "," not in status:
                    query += " and [jobStatus] %s '%s'" % (op[0],status)
                else:
                    status_list = [ " [jobStatus] %s '%s' " % (op[0],s) for s in status.split(',')]
                    status_statement = (" "+op[1]+" ").join(status_list)
                    query += " and ( %s ) " % status_statement                       

            query += " order by [jobTime] Desc"
            start_time1 = timeit.default_timer()
            cursor.execute(query)
            elapsed1 = timeit.default_timer() - start_time1
            start_time2 = timeit.default_timer()
            data = cursor.fetchall()
            elapsed2 = timeit.default_timer() - start_time2
            logger.info ("(fetchall time: %f)" % (elapsed2))
            for (jobId,jobName,userName, vcName,jobStatus,jobStatusDetail, jobType, jobDescriptionPath, jobDescription, jobTime, endpoints, jobParams,errorMsg, jobMeta) in data:
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
        logger.info ("DataHandler: get job list for user %s , time elapsed %f s (SQL query time: %f)" % (userName, elapsed, elapsed1))
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
        query = "SELECT [jobId],[familyToken],[isParent],[jobName],[userName],[vcName], [jobStatus], [jobStatusDetail], [jobType], [jobDescriptionPath], [jobDescription], [jobTime], [endpoints], [jobParams],[errorMsg] ,[jobMeta]  FROM [%s] where [%s] = '%s' " % (self.jobtablename,key,expected)
        cursor.execute(query)
        columns = [column[0] for column in cursor.description]
        ret = [dict(zip(columns, row)) for row in cursor.fetchall()]
        self.conn.commit()
        cursor.close()
        elapsed = timeit.default_timer() - start_time
        logger.info ("DataHandler: get job details with query %s=%s , time elapsed %f s" % (key, expected, elapsed))
        return ret


    def AddCommand(self,jobId,command):
        try:
            start_time = timeit.default_timer()
            sql = """INSERT INTO [%s] (jobId, command) VALUES (?,?)""" % self.commandtablename
            cursor = self.conn.cursor()
            cursor.execute(sql, jobId, command)
            self.conn.commit()
            cursor.close()
            elapsed = timeit.default_timer() - start_time
            logger.info ("DataHandler: add command to database, jobId: %s , time elapsed %f s" % (jobId, elapsed))
            return True
        except Exception as e:
            logger.error('Exception: '+ str(e))
            return False


    def GetPendingCommands(self):
        start_time = timeit.default_timer()
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
        self.conn.commit()
        cursor.close()
        elapsed = timeit.default_timer() - start_time
        logger.info ("DataHandler: get pending command , time elapsed %f s" % (elapsed))
        return ret    


    def FinishCommand(self,commandId):
        try:
            start_time = timeit.default_timer()
            sql = """update [%s] set status = 'run' where [id] = '%s' """ % (self.commandtablename, commandId)
            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            cursor.close()
            elapsed = timeit.default_timer() - start_time
            logger.info ("DataHandler: set command %s as finished , time elapsed %f s" % (commandId, elapsed))
            return True
        except Exception as e:
            logger.error('Exception: '+ str(e))
            return False


    def GetCommands(self, jobId):
        start_time = timeit.default_timer()
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
        self.conn.commit()
        cursor.close()
        elapsed = timeit.default_timer() - start_time
        logger.info ("DataHandler: get command list for job %s , time elapsed %f s" % (jobId, elapsed))
        return ret    


    def GetPendingJobs(self):
        start_time = timeit.default_timer()
        cursor = self.conn.cursor()
        query = "SELECT [jobId],[jobName],[userName], [vcName], [jobStatus], [jobType], [jobDescriptionPath], [jobDescription], [jobTime], [endpoints], [jobParams],[errorMsg] ,[jobMeta] FROM [%s] where [jobStatus] <> 'error' and [jobStatus] <> 'failed' and [jobStatus] <> 'finished' and [jobStatus] <> 'killed' order by [jobTime] DESC" % (self.jobtablename)
        cursor.execute(query)
        ret = []
        for (jobId,jobName,userName, vcName, jobStatus, jobType, jobDescriptionPath, jobDescription, jobTime, endpoints, jobParams,errorMsg, jobMeta) in cursor:
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
        logger.info ("DataHandler: get pending jobs , time elapsed %f s" % (elapsed))
        return ret        


    def SetJobError(self,jobId,errorMsg):
        try:
            start_time = timeit.default_timer()
            sql = """update [%s] set jobStatus = 'error', [errorMsg] = ? where [jobId] = '%s' """ % (self.jobtablename,jobId)
            cursor = self.conn.cursor()
            cursor.execute(sql,errorMsg)
            self.conn.commit()
            cursor.close()
            elapsed = timeit.default_timer() - start_time
            logger.info ("DataHandler: set job %s error status in database, time elapsed %f s" % (jobId, elapsed))
            return True
        except Exception as e:
            logger.error('Exception: '+ str(e))
            return False        


    def UpdateJobTextField(self,jobId,field,value):
        try:
            start_time = timeit.default_timer()
            sql = """update [%s] set [%s] = ? where [jobId] = '%s' """ % (self.jobtablename,field, jobId)
            cursor = self.conn.cursor()
            cursor.execute(sql,value)
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
        query = "SELECT [jobId], [%s] FROM [%s] where [jobId] = '%s' " % (field, self.jobtablename,jobId)
        ret = None
        try:
            cursor.execute(query)
            for (jobId, value) in cursor:
                ret = value
        except Exception, e:
            logger.error('Exception: '+ str(e))
            pass
        self.conn.commit()
        cursor.close()
        elapsed = timeit.default_timer() - start_time
        logger.info ("DataHandler: get filed %s of job %s , time elapsed %f s" % (field, jobId, elapsed))
        return ret

    def AddandGetJobRetries(self,jobId):
        start_time = timeit.default_timer()
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
        self.conn.commit()
        cursor.close()
        elapsed = timeit.default_timer() - start_time
        logger.info ("DataHandler: get and update retries for job %s , time elapsed %f s" % (jobId, elapsed))
        return ret


    def UpdateClusterStatus(self,clusterStatus):
        try:
            start_time = timeit.default_timer()
            sql = """INSERT INTO [%s] (status) VALUES (?)""" % self.clusterstatustablename
            cursor = self.conn.cursor()
            status = base64.b64encode(json.dumps(clusterStatus))
            cursor.execute(sql,status)
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
        query = "SELECT TOP 1 [time], [status] FROM [%s] order by [time] DESC" % (self.clusterstatustablename)
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
        self.conn.commit()
        cursor.close()
        elapsed = timeit.default_timer() - start_time
        logger.info ("DataHandler: get cluster status , time elapsed %f s" % (elapsed))
        return ret, time


    def GetUsers(self):
        start_time = timeit.default_timer()
        cursor = self.conn.cursor()
        query = "SELECT [identityName],[uid] FROM [%s]" % (self.identitytablename)
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
        logger.info ("DataHandler: get users, time elapsed %f s" % ( elapsed))
        return ret


    def GetActiveJobsCount(self):
        cursor = self.conn.cursor()
        query = "SELECT count(ALL id) as c FROM [%s] where [jobStatus] <> 'error' and [jobStatus] <> 'failed' and [jobStatus] <> 'finished' and [jobStatus] <> 'killed' " % (self.jobtablename)
        cursor.execute(query)
        ret = 0
        for c in cursor:
            ret = c[0]
        self.conn.commit()
        cursor.close()

        return ret        

    def GetALLJobsCount(self):
        cursor = self.conn.cursor()
        query = "SELECT count(ALL id) as c FROM [%s]" % (self.jobtablename)
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
        self.conn = SQLConnManager.ReturnConnection(self.conn)

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
