import pyodbc
import json
import time
from config import config

class DataHandler:
    def __init__(self):

        self.server = config["database"]["hostname"] 
        self.database = config["database"]["database"]
        self.username = config["database"]["username"]
        self.password = config["database"]["password"]
        # self.driver = '/usr/lib/x86_64-linux-gnu/libodbc.so'
        self.driver = '{ODBC Driver 13 for SQL Server}'
        self.connstr = 'DRIVER='+self.driver+';PORT=1433;SERVER='+self.server+';PORT=1433;DATABASE='+self.database+';UID='+self.username+';PWD='+self.password
        print "Try to connect with string: " + self.connstr
        self.conn = pyodbc.connect(self.connstr)
        print "Connecting to server ..."


        self.add_cluster_info = """ 
                                   INSERT INTO cluster_info 
                                   ([clusterId], [k], [v]) 
                                   VALUES (?,?,?)    
                                """

        self.add_report = """ insert into report (host_IP,clusterId,role,clientIP,sysId) values  (?, ?, ?, ?, ?) """

    def AddNode(self, data):
        cursor = self.conn.cursor()
        cursor.execute(self.add_report, data["hostIP"], data["clusterId"], data["role"], data["clientIP"], data["sysId"])
        self.conn.commit()
        cursor.close()


    def GetNodes(self,role,clusterId):
        cursor = self.conn.cursor()
        query = "SELECT host_IP,clusterId,role, clientIP, time FROM report where role = '"+role+"' and clusterId = '"+clusterId+"' group by sysId "
        query = """ select a.host_IP,a.clusterId,a.role,a.clientIP, a.time from report a
                    left join report b
                    on a.sysId=b.sysId
                    and a.[time] < b.[time]
                    where b.sysId is NULL 
                    and a.[time] >= DATEADD (hour, -1, getdate())
                    and a.clusterId='%s' 
                    and a.role = '%s'
                    """ % (clusterId,role)

        cursor.execute(query)
        ret = []
        for (hostIP,clusterId,role, clientIP, dtime) in cursor:
            record = {}
            record["hostIP"] = hostIP.strip()
            record["clusterId"] = clusterId.strip()
            record["role"] = role.strip()
            record["clientIP"] = clientIP.strip()
            record["time"] = time.mktime(dtime.timetuple())
            ret.append(record)
        cursor.close()

        return ret

    def AddClusterInfo(self, data):
        cursor = self.conn.cursor()
        cursor.execute(self.add_cluster_info, data["clusterId"], data["key"], data["value"])
        self.conn.commit()
        cursor.close()


    def GetClusterInfo(self,clusterId,key):
        cursor = self.conn.cursor()
        query = ("SELECT TOP 1 [k], [v] FROM cluster_info where [k] = '"+key+"' and [clusterId] = '"+clusterId+"' order by [time] desc")
        cursor.execute(query)
        value = None
        for (k,v) in cursor:
            value = v.strip()
        cursor.close()
        return value        
    

    def DeleteCluster(self,clusterId):
        cursor = self.conn.cursor()
        query = ("DELETE FROM cluster_info where clusterId = '"+clusterId+"'")
        cursor.execute(query)
        cursor.close()
        self.conn.commit()


    def Close(self):
        self.conn.close()

if __name__ == '__main__':
    TEST_INSERT_NODE = False
    TEST_GET_NODE = False
    TEST_INSTER_CLUSTER_INFO = True
    dataHandler = DataHandler()
    
    if TEST_INSERT_NODE:
        jobParams = {}
        jobParams["hostIP"] = "10.10.10.10"
        jobParams["clusterId"] = "1234556"
        jobParams["role"] = "worker"
        jobParams["clientIP"] =  "10.10.10.10"
        jobParams["sysId"] = "ADSCASDcAE!EDASCASDFD"
        
        dataHandler.AddNode(jobParams)
    if TEST_GET_NODE:
        print dataHandler.GetNodes("worker","1234556")

    if TEST_INSTER_CLUSTER_INFO:
        data = {}
        data["clusterId"] = "1234"
        data["key"] = "key"
        data["value"] = "value"
        dataHandler.AddClusterInfo(data)

    print dataHandler.GetClusterInfo("1234","key")
    dataHandler.DeleteCluster("1234")