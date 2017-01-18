import mysql.connector
import json
import time

class DataHandler:
	def __init__(self):
		self.conn = mysql.connector.connect(user="dlworkspace", password="",database="dlworkspace")
		self.add_cluster_info = ("INSERT INTO cluster_info "
               "(`clusterId`, `key`, `value`) "
               "VALUES (%(clusterId)s, %(key)s, %(value)s)")		

		self.add_report = ("INSERT INTO report "
               "(`hostIP`, `clusterId`, `role`, `clientIP` ) "
               "VALUES (%(hostIP)s, %(clusterId)s, %(role)s, %(clientIP)s)")	

	def AddNode(self, data):
		cursor = self.conn.cursor()
		cursor.execute(self.add_report, data)
		id = cursor.lastrowid
		self.conn.commit()
		cursor.close()


	def GetNodes(self,role,clusterId):
		cursor = self.conn.cursor()
		query = ("SELECT hostIP,clusterId,role, clientIP, time FROM report where time > NOW() - 1200 and role = '"+role+"' and clusterId = '"+clusterId+"'")
		cursor.execute(query)
		ret = []
		for (hostIP,clusterId,role, clientIP, dtime) in cursor:
			record = {}
			record["hostIP"] = hostIP
			record["clusterId"] = clusterId
			record["role"] = role
			record["clientIP"] = clientIP
			record["time"] = time.mktime(dtime.timetuple())
		  	ret.append(record)
		cursor.close()

		return ret

	def AddClusterInfo(self, data):
		cursor = self.conn.cursor()
		cursor.execute(self.add_cluster_info, data)
		id = cursor.lastrowid
		self.conn.commit()
		cursor.close()


	def GetClusterInfo(self,clusterId,key):
		cursor = self.conn.cursor()
		query = ("SELECT `key`, `value` FROM cluster_info where `key` = '"+key+"' and `clusterId` = '"+clusterId+"' order by time desc limit 1")
		cursor.execute(query)
		value = None
		for (k,v) in cursor:
			value = v
		cursor.close()
		return value		
	

	def DeleteCluster(self,clusterId):
		cursor = self.conn.cursor()
		query = ("DELETE FROM cluster_info where clusterId = '"+clusterId+"'")
		cursor.execute(query)
		cursor.close()


	def Close(self):
		self.conn.close()

if __name__ == '__main__':
	TEST_INSERT_JOB = False
	TEST_QUERY_JOB_LIST = True
	dataHandler = DataHandler()
	
	if TEST_INSERT_JOB:
		jobParams = {}
		jobParams["id"] = "dist-tf-00001"
		jobParams["job-name"] = "dist-tf"
		jobParams["user-id"] = "hongzl"
		jobParams["job-meta-path"] = "/dlws/jobfiles/***"
		jobParams["job-meta"] = "ADSCASDcAE!EDASCASDFD"
		
		dataHandler.AddJob(jobParams)
	
	if TEST_QUERY_JOB_LIST:
		print dataHandler.GetJobList()
