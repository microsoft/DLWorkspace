using System;
using System.Collections.Generic;
using System.Text;
using System.Data;
using System.Data.SqlClient;

namespace DLWorkspaceUtils
{
    public class DataHandler
    {
        private SqlConnection conn { get; set; }
        private string _jobTableName { get; set; }
        private string _clusterstatustablename { get; set; }
        public DataHandler()
        {
            OpenConn();
        }
        private void OpenConn()
        {
            string _server = config.database_hostname;
            string _database = config.database_databasename;
            string _username = config.database_username;
            string _password = config.database_password;
            _jobTableName = "jobs-" + config.clusterId;
            _clusterstatustablename = "clusterstatus-" + config.clusterId;

            if (conn == null || conn.State == ConnectionState.Closed || conn.State == ConnectionState.Broken)
            {
                string connStr = string.Format("Server={0};Initial Catalog={1};Persist Security Info=False;User ID={2};Password={3};MultipleActiveResultSets=False;Encrypt=True;TrustServerCertificate=False;Connection Timeout=30;", _server, _database, _username, _password);
                conn = new SqlConnection(connStr);
                conn.Open();
            }
        }

        private void CloseConn()
        {
            if (conn != null && conn.State != ConnectionState.Closed && conn.State != ConnectionState.Broken)
            {
                conn.Close();
            }
            if (conn != null)
            {
                conn.Dispose();
            }
        }

        ~DataHandler()
        {

            CloseConn();
        }

        public void Close()
        {
            CloseConn();
        }

        public List<Job> GetJobList()
        {

            List<Job> jobs = new List<Job>();

            string queryStatement = string.Format("SELECT [jobId],[jobName],[userName], [jobStatus], [jobType], [jobDescriptionPath], [jobDescription], [jobTime], [endpoints], [jobParams],[errorMsg] FROM [{0}]", _jobTableName);

            using (SqlCommand cmd = new SqlCommand(queryStatement, conn))
            {
                using (SqlDataReader dataReader = cmd.ExecuteReader())
                {
                    while (dataReader.Read() == true)
                    {
                        Job job = new Job();
                        job.jobId = dataReader["jobId"].ToString();
                        job.jobName = dataReader["jobName"].ToString();
                        job.userName = dataReader["userName"].ToString();
                        job.jobStatus = dataReader["jobStatus"].ToString();
                        job.jobType = dataReader["jobType"].ToString();
                        job.jobDescriptionPath = dataReader["jobDescriptionPath"].ToString();
                        job.jobDescription = dataReader["jobDescription"].ToString();
                        job.jobTime = dataReader["jobTime"].ToString();
                        job.endpoints = dataReader["endpoints"].ToString();
                        job.jobParams = JobParams.Deserialize(System.Text.Encoding.UTF8.GetString(Convert.FromBase64String(dataReader["jobParams"].ToString())));
                        job.errorMsg = dataReader["errorMsg"].ToString();
                        jobs.Add(job);
                    }
                }
            }

            return jobs;
        }



        public Job GetJob(string jobId)
        {

            Job job = null;
            string queryStatement = string.Format("SELECT TOP 1 [jobId],[jobName],[userName], [jobStatus], [jobType], [jobDescriptionPath], [jobDescription], [jobTime], [endpoints], [jobParams],[errorMsg] FROM [{0}] where cast([jobId] as nvarchar(max)) = N'{1}' ", _jobTableName, jobId);

            using (SqlCommand cmd = new SqlCommand(queryStatement, conn))
            {
                using (SqlDataReader dataReader = cmd.ExecuteReader())
                {
                    if (dataReader.Read() == true)
                    {
                        job = new Job();
                        job.jobId = dataReader["jobId"].ToString();
                        job.jobName = dataReader["jobName"].ToString();
                        job.userName = dataReader["userName"].ToString();
                        job.jobStatus = dataReader["jobStatus"].ToString();
                        job.jobType = dataReader["jobType"].ToString();
                        job.jobDescriptionPath = dataReader["jobDescriptionPath"].ToString();
                        job.jobDescription = dataReader["jobDescription"].ToString();
                        job.jobTime = dataReader["jobTime"].ToString();
                        job.endpoints = dataReader["endpoints"].ToString();
                        job.jobParams = JobParams.Deserialize(System.Text.Encoding.UTF8.GetString(Convert.FromBase64String(dataReader["jobParams"].ToString())));
                        job.errorMsg = dataReader["errorMsg"].ToString();
                    }
                }
            }

            return job;
        }


        public string GetJobTextField(string jobId, string field)
        {

            string queryStatement = string.Format("SELECT TOP 1 [{0}] FROM [{1}] where cast([jobId] as nvarchar(max)) = N'{2}'", field, _jobTableName, jobId);
            using (SqlCommand cmd = new SqlCommand(queryStatement, conn))
            {
                using (SqlDataReader dataReader = cmd.ExecuteReader())
                {
                    if (dataReader.Read() == true)
                    {
                        return dataReader[field].ToString();
                    }
                }
            }

            return null;
        }


        public Tuple<string, string> GetClusterStatus()
        {
            Tuple<string, string> ret = null;
            string queryStatement = string.Format("SELECT TOP 1 [time], [status] FROM [{0}] order by [time] DESC", _clusterstatustablename);
            using (SqlCommand cmd = new SqlCommand(queryStatement, conn))
            {
                using (SqlDataReader dataReader = cmd.ExecuteReader())
                {
                    if (dataReader.Read() == true)
                    {
                        ret = new Tuple<string, string>(System.Text.Encoding.UTF8.GetString(Convert.FromBase64String(dataReader["status"].ToString())),  dataReader["time"].ToString());
                    }
                }
            }
            return ret;
        }

        public bool KillJob(string jobId)
        {
            try
            {
                string queryStatement = string.Format("update [{0}] set jobStatus = 'killing' where cast([jobId] as nvarchar(max)) = N'{1}' ", _jobTableName, jobId);
                using (SqlCommand cmd = new SqlCommand(queryStatement, conn))
                {
                    cmd.ExecuteNonQuery();
                }
                return true;
            }
            catch (Exception e)
            {
                return false;
            }
        }


        public bool AddJob(Job job)
        {
            try
            {
                string jobParams = Convert.ToBase64String(System.Text.Encoding.UTF8.GetBytes(job.jobParams.ToString()));
                string queryStatement = string.Format("INSERT INTO [{0}] (jobId, jobName, userName, jobType,jobParams ) VALUES ('{1}','{2}','{3}','{4}','{5}') ", _jobTableName,job.jobId,job.jobName,job.userName,job.jobType,jobParams);
                using (SqlCommand cmd = new SqlCommand(queryStatement, conn))
                {
                    cmd.ExecuteNonQuery();
                }

                return true;
            }
            catch (Exception e)
            {
                return false;
            }
        }
    }
}
