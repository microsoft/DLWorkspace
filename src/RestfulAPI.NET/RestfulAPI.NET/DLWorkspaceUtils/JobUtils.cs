using System;
using System.Collections.Generic;
using System.Text;
using Newtonsoft.Json;
using System.IO;

namespace DLWorkspaceUtils
{
    public class JobUtils
    {
        public static string SubmitJob(string jobJsonStr)
        {
            Dictionary<string, string> ret = new Dictionary<string, string>();
            DataHandler dataHandler = new DataHandler();

            Job job = Job.Deserialize(jobJsonStr);
            if (job.jobId == null || job.jobId.Trim().Length == 0)
            {
                job.jobId = Guid.NewGuid().ToString();
            }


            job.jobParams.jobId = job.jobId;
            job.jobParams.jobName = job.jobName;
            job.jobParams.jobType = job.jobType;

            if (job.jobParams.jobPath == null || job.jobParams.jobPath.Trim().Length == 0)
            {
                job.jobParams.jobPath = job.userName.Replace("@microsoft.com","").Trim()+"/jobs/"+ DateTime.Now.ToString("yyMMdd") + "/" + job.jobId;
            }


            if (job.jobParams.workPath == null || job.jobParams.workPath.Trim().Length == 0)
            {
                if (!ret.ContainsKey("error"))
                {
                    ret.Add("error", "work-path cannot be empty.");
                }
            }

            if (job.jobParams.dataPath == null || job.jobParams.dataPath.Trim().Length == 0)
            {
                if (!ret.ContainsKey("error"))
                {
                    ret.Add("error", "data-path cannot be empty.");
                }
            }


            if (job.jobParams.logDir != null && job.jobParams.logDir.Trim().Length > 0)
            {
                Job tensorboardJob = Job.Deserialize(job.ToString());
                tensorboardJob.jobId = Guid.NewGuid().ToString();
                tensorboardJob.jobName = "tensorboard-" + tensorboardJob.jobName;
                tensorboardJob.jobType = "visualization";
                tensorboardJob.jobParams.cmd = "tensorboard --logdir " + tensorboardJob.jobParams.logDir + " --host 0.0.0.0";
                tensorboardJob.jobParams.gpu = 0;
                tensorboardJob.jobParams.interactivePort = "6006";

                tensorboardJob.jobParams.jobId = tensorboardJob.jobId;
                tensorboardJob.jobParams.jobName = tensorboardJob.jobName;
                tensorboardJob.jobParams.jobType = tensorboardJob.jobType;


                if (!ret.ContainsKey("error"))
                {
                    if (!dataHandler.AddJob(tensorboardJob))
                    {
                        ret.Add("error", "Cannot schedule tensorboard job.");
                    }
                }
            }
           

            if (!ret.ContainsKey("error"))
            {
                if (dataHandler.AddJob(job))
                {
                    ret.Add("jobId", "application_"+job.jobId);
                }
                else
                {
                    ret.Add("error", "Cannot schedule job. Cannot add job into database.");
                }
            }
            dataHandler.Close();

            return JsonConvert.SerializeObject(ret);
        }
        public static List<Job> GetJobList()
        {
            DLWorkspaceUtils.DataHandler dataHandler = new DLWorkspaceUtils.DataHandler();
            List<Job> jobs = dataHandler.GetJobList();
            dataHandler.Close();
            return jobs;
        }
        public static bool KillJob(string jobId)
        {
            DLWorkspaceUtils.DataHandler dataHandler = new DLWorkspaceUtils.DataHandler();
            bool ret = dataHandler.KillJob(jobId);
            dataHandler.Close();
            return ret;
        }
        public static Job GetJobDetail(string jobId)
        {
            Dictionary<string, string> ret = new Dictionary<string, string>();
            DLWorkspaceUtils.DataHandler dataHandler = new DLWorkspaceUtils.DataHandler();
            Job job = dataHandler.GetJob(jobId);
            try
            {
                string log = dataHandler.GetJobTextField(jobId, "jobLog");
                if (log != null)
                {
                    job.log = log;
                }
            }
            catch(Exception e)
            {
                job.log = "fail-to-get-logs";
            }

            dataHandler.Close();
            return job;

        }
    }
}
