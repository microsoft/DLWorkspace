from config import config
import mysql.connector
import json

class DataHandler:
	def __init__(self):
		self.conn = mysql.connector.connect(host=config["mysql"]["hostname"], user=config["mysql"]["username"], password=config["mysql"]["password"],database=config["mysql"]["database"])
		self.add_job = ("INSERT INTO jobs "
               "(job_id, job_name, user_id, job_meta_path,job_meta ) "
               "VALUES (%(id)s, %(job-name)s, %(user-id)s, %(job-meta-path)s, %(job-meta)s)")		
	def AddJob(self, jobParams):
		cursor = self.conn.cursor()
		cursor.execute(self.add_job, jobParams)
		id = cursor.lastrowid
		self.conn.commit()
		cursor.close()

	def DelJob(self,jobId):
		cursor = self.conn.cursor()
		query = ("delete from jobs where job_id = '"+jobId+"' ")
		cursor.execute(query)
		self.conn.commit()
		cursor.close()



	def GetJobList(self):
		cursor = self.conn.cursor()
		query = ("SELECT job_id,job_name,user_id, job_meta_path, time, status, job_meta FROM jobs ")
		cursor.execute(query)
		ret = []
		for (job_id,job_name,user_id, job_meta_path, time, status, job_meta) in cursor:
			record = {}
			record["job_id"] = job_id
			record["job_name"] = job_name
			record["user_id"] = user_id
			record["job_meta_path"] = job_meta_path
			record["time"] = time
			record["status"] = status
			record["job_meta"] = job_meta
		  	ret.append(record)
		cursor.close()

		return ret
	


	def GetJob(self,jobId):
		cursor = self.conn.cursor()
		query = ("SELECT job_id,job_name,user_id, job_meta_path, time, status, job_meta FROM jobs "
				"where job_id = '"+jobId+"' ")
		cursor.execute(query)
		ret = []
		for (job_id,job_name,user_id, job_meta_path, time, status, job_meta) in cursor:
			record = {}
			record["job_id"] = job_id
			record["job_name"] = job_name
			record["user_id"] = user_id
			record["job_meta_path"] = job_meta_path
			record["time"] = time
			record["status"] = status
			record["job_meta"] = job_meta
		  	ret.append(record)
		cursor.close()
		return ret
	def ChangeStatus(self,jobId, newStatus):
		pass
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
