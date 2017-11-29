using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using DLWorkspaceUtils;
using Newtonsoft.Json;
using RestfulAPI.NET.Models;
using System.IO;
using System.Text.RegularExpressions;


namespace RestfulAPI.NET.Controllers
{
    [Produces("application/json")]
    [Route("api/Jobs")]
    public class JobsController : Controller
    {
        // GET: api/Jobs
        [HttpGet]
        public IEnumerable<string> Get()
        {
            return new string[] { "value1", "value2" };
        }

        // GET: api/Jobs/5
        [HttpGet("{op}", Name = "Get")]
        public string Get(string op)
        {
            string ret = "test";
            if (op == "SubmitJob")
            {
                DLWorkspaceUtils.Job job = new Job();
                job.jobParams = new JobParams();
                job.jobName = HttpContext.Request.Query["jobName"];
                job.jobType = HttpContext.Request.Query["jobType"];
                job.userName = HttpContext.Request.Query["userName"];
                job.jobParams.gpu = Int32.Parse(HttpContext.Request.Query["resourcegpu"]);
                job.jobParams.workPath = HttpContext.Request.Query["workPath"];
                job.jobParams.dataPath = HttpContext.Request.Query["dataPath"];
                job.jobParams.dockerImage = HttpContext.Request.Query["image"];
                job.jobParams.cmd = HttpContext.Request.Query["cmd"];
                job.jobParams.interactivePort = HttpContext.Request.Query["interactivePort"];
                job.jobParams.jobtrainingtype = HttpContext.Request.Query["jobtrainingtype"];
                job.jobParams.runningasroot = HttpContext.Request.Query["runningasroot"];
                job.jobParams.userName = HttpContext.Request.Query["userName"];
                job.jobParams.userId = HttpContext.Request.Query["userId"];
                job.jobParams.containerUserId = HttpContext.Request.Query["containerUserId"];


                if (job.jobParams.containerUserId == null)
                {
                    if (job.jobParams.runningasroot != null && job.jobParams.runningasroot == "1")
                    {
                        job.jobParams.containerUserId = "0";
                    }
                    else
                    {
                        job.jobParams.containerUserId = job.jobParams.userId;
                    }
                }

                ret = DLWorkspaceUtils.JobUtils.SubmitJob(job.ToString());

            }
            else if (op == "submitPhilly")
            {
                

                DLWorkspaceUtils.Job job = new Job();
                job.jobParams = new JobParams();


//CMD += "configFile=$USERNAME%2FloopTest.lua&"
//CMD += "minGPUs=1&"
//CMD += "name=cust-test!~!~!1&"
//CMD += "isdebug=false&"
//CMD += "iscrossrack=false&"
//CMD += "inputDir=%2Fhdfs%2F$VC%2F$USERNAME%2FData&"
//CMD += "userName=$USERNAME"

                job.jobParams.workPath = HttpContext.Request.Query["workPath"];
                job.jobParams.dataPath = HttpContext.Request.Query["dataPath"];


                job.jobName = HttpContext.Request.Query["JobName"];
                job.jobParams.gpu = Int32.Parse(HttpContext.Request.Query["MinGPUs"]);
                job.jobParams.dockerImage = HttpContext.Request.Query["CustomDockerName"];

                string toolType = HttpContext.Request.Query["toolType"];
                if (!job.jobParams.dockerImage.Contains("/") && toolType != null && toolType == "cust")
                {
                    job.jobParams.dockerImage = "master:5000/rr1-prod/infrastructure:"+ job.jobParams.dockerImage;
                }


                job.jobParams.cmd = HttpContext.Request.Query["cmd"];

                job.jobType = "training";

                job.jobParams.userName = HttpContext.Request.Query["UserName"];
                job.jobParams.userId = "-1";

                job.jobParams.runningasroot = "1";
                job.jobParams.containerUserId = "0";

                ret = DLWorkspaceUtils.JobUtils.SubmitJob(job.ToString());
            }
            else if (op == "submit")
            {
                Dictionary<string, string> retdict = new Dictionary<string, string>();
                retdict.Add("jobId", Guid.NewGuid().ToString());
                ret = JsonConvert.SerializeObject(retdict);
            }
            else if (op == "list")
            {
                Dictionary<string, string> retdict = new Dictionary<string, string>();
                retdict.Add("phillyversion", "116");
                ret = JsonConvert.SerializeObject(retdict);
            }
            else if (op == "status")
            {
                string jobId = HttpContext.Request.Query["jobId"];
                jobId = jobId.Replace("application_", "");
                Job job = JobUtils.GetJobDetail(jobId);

                Dictionary<string, string> retdict = new Dictionary<string, string>();

                string dir = @"\\storage.cly.philly.selfhost.corp.microsoft.com\"+ job.jobParams.dataPath.Replace("/","\\") + "\\"+jobId+"\\";
                retdict.Add("dir", dir);
                retdict.Add("scratch", job.jobParams.workPath);
                retdict.Add("evalErr", "0");
                retdict.Add("finishDateTime", job.jobTime.ToString());
                retdict.Add("gpus", job.jobParams.gpu.ToString());
                retdict.Add("name", job.jobName);
                retdict.Add("appId", "application_" + job.jobId);
                retdict.Add("retries", "0");
                retdict.Add("preempt", "0");
                retdict.Add("progress", "0");
                retdict.Add("queueDateTime", job.jobTime.ToString());
                retdict.Add("startDateTime", job.jobTime.ToString());


                string status = job.jobStatus;
                
                // philly status: Pass, Queued, Running, Failed, Killed 

                if (status == "finished")
                {
                    status = "Pass";
                }
                else if (status == "failed" || status == "error")
                {
                    status = "Failed";
                }
                else if (status == "queued" || status == "scheduling")
                {
                    status = "Queued";
                }
                else if (status == "running" || status == "killing")
                {
                    status = "Running";
                }
                else if (status == "Killed")
                {
                    status = "Killed";
                }


                retdict.Add("status", status);
                retdict.Add("userName", job.userName.Replace("@microsoft.com",""));
                retdict.Add("queue", "default");
                retdict.Add("vc", job.jobParams.vcId);


                ret = JsonConvert.SerializeObject(retdict);
                Console.WriteLine(ret);
            }
            else if (op == "abort")
            {
                Dictionary<string, string> retdict = new Dictionary<string, string>();
                string jobId = HttpContext.Request.Query["jobId"];
                jobId = jobId.Replace("application_", "");
                retdict.Add("jobKilled", jobId);
                ret = JsonConvert.SerializeObject(retdict);
                DLWorkspaceUtils.JobUtils.KillJob(jobId);
                Console.WriteLine(jobId);
            }
            return ret;
        }



        [Route("restapi/submit")]
        // POST: api/Jobs
        [HttpPost("submit")]
        public string Post([FromBody]AetherRequestParams reqParams)
        {
            Console.WriteLine(reqParams.ToString());
            DLWorkspaceUtils.Job job = new Job();
            job.jobParams = new JobParams();

            string username = reqParams.UserName;
            if (username.Contains("@"))
            {
                username = username.Split(new char[] { '@' })[0];
            }
            if (username.Contains("\\"))
            {
                username = username.Split(new char[] { '\\' })[1];
            }


            string fullUsername = username + "@microsoft.com";



            string configFilename = Path.GetFileName(reqParams.ConfigFile);
            string workPath = Path.GetDirectoryName(reqParams.ConfigFile);
            if (workPath[0] == '/')
            {
                workPath = workPath.Substring(1);
            }
            
            job.jobParams.workPath = workPath;



            if (reqParams.InputDirectory != null && reqParams.InputDirectory.Trim().Length > 0)
            {
                job.jobParams.dataPath = reqParams.InputDirectory;
            }
            else
            {
                foreach (var input in reqParams.Inputs)
                {
                    if (input.Name== "datadir")
                    {
                        //hard-code for philly setup
                        job.jobParams.dataPath = input.Path.Replace("/hdfs/","");
                        break;
                    }
                }
            }


            //hard-code for philly setup
            if (Path.GetExtension(configFilename) == ".py")
            {
                job.jobParams.cmd = "/usr/local/bin/apython3 " + Path.Combine("/work", configFilename);
                job.jobParams.cmd += " -datadir /data";
                job.jobParams.cmd += " -logdir /job/logs/1/out";
                job.jobParams.cmd += " -outputdir /job/models";
                job.jobParams.cmd += " -loadsnapshotdir /job/models";
                job.jobParams.cmd += " -ngpu "+ reqParams.MinGpus;
                job.jobParams.cmd += " -gpus 0";

                string extraParams = reqParams.ExtraParams.Replace("PHILLY_OUTPUTDIR", "/job/models").Replace("PHILLY_LOGDIR", "/job/logs/1/out").Replace("PHILLY_DATADIR", "/data/").Replace("PHILLY_CONFIG_DIR", "/work/");


                Regex rgx = new Regex("--pp .* -- ");
                extraParams = rgx.Replace(extraParams, "");


                job.jobParams.cmd += " " + extraParams;



            }
            else
            {
                job.jobParams.cmd = "/bin/bash -c '" + Path.Combine("/work", configFilename) ;

                job.jobParams.cmd += " -datadir /data/";
                job.jobParams.cmd += " -logdir /job/";
                job.jobParams.cmd += " -outputdir /job/";
                job.jobParams.cmd += " -loadsnapshotdir /job/models/";
                job.jobParams.cmd += " -ngpu " + reqParams.MinGpus;
                job.jobParams.cmd += " -gpus 0";

                job.jobParams.cmd += " " + reqParams.ExtraParams + "'";
            }


            job.jobParams.mountpoints = new List<DLWorkspaceUtils.MountPoint>();
            DLWorkspaceUtils.MountPoint hdfsmp = new DLWorkspaceUtils.MountPoint();
            hdfsmp.name = "hdfs";
            hdfsmp.hostPath = "/hadoopmnt";
            hdfsmp.containerPath = "/hdfs";
            job.jobParams.mountpoints.Add(hdfsmp);

            if (reqParams.PreviousModelPath != null)
            {
                DLWorkspaceUtils.MountPoint mp = new DLWorkspaceUtils.MountPoint();
                mp.name = "prevmodel";
                mp.hostPath = "/dlwsdata/storage/"+ reqParams.VcId + "/"+reqParams.PreviousModelPath.Replace("/hdfs/", "");
                mp.containerPath = "/prevModel";
                job.jobParams.mountpoints.Add(mp);
                job.jobParams.cmd = " cp -r /prevModel/* /job/models/ ; " + job.jobParams.cmd;
            }

            job.jobId = Guid.NewGuid().ToString();

            job.jobParams.cmd += "  && ( mkdir -p /data/"+ job.jobId+"/models && cp -r /job/models/* /data/"+ job.jobId+"/models/ )  ";

            job.jobParams.vcId = reqParams.VcId;

            job.jobName = reqParams.JobName;

            if (job.jobName.Length > 62)
            {
                job.jobName = job.jobName.Substring(0, 62);
            }


            job.jobParams.gpu = reqParams.MinGpus;
            

            string toolType = reqParams.toolType;
            //hard-code for philly setup
            if (!reqParams.CustomDockerName.Contains("/"))
            {
                job.jobParams.dockerImage = "mlcloudreg.westus.cloudapp.azure.com:5000/philly/" + reqParams.CustomDockerName;
            }
            else
            {
                job.jobParams.dockerImage = reqParams.CustomDockerName;
            }

           

            job.jobType = "training";
            job.jobParams.jobtrainingtype = "RegularJob";

            job.userName = fullUsername;
            job.jobParams.userName = fullUsername;
            job.jobParams.userId = "0";

            job.jobParams.runningasroot = "0";
            job.jobParams.containerUserId = "0";

            job.jobParams.interactivePort = "";
            job.jobParams.jobPath = "";
            job.jobParams.logDir = "";

            Console.WriteLine(job.ToString());

            string ret = DLWorkspaceUtils.JobUtils.SubmitJob(job.ToString());
            return ret;
        }
        

    }
}
