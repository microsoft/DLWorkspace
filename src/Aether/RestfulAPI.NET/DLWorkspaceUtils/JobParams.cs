using System;
using System.Collections.Generic;
using System.Text;
using System.Runtime.Serialization;
using Newtonsoft.Json;


namespace DLWorkspaceUtils
{
    [DataContract]
    public class JobParams
    {

        [DataMember]
        public string jobId { get; set; }

        [DataMember]
        public string jobName { get; set; }

        [DataMember(Name = "resourcegpu")]
        public int gpu { get; set; }

        [DataMember]
        public string workPath { get; set; }

        [DataMember]
        public string dataPath { get; set; }

        [DataMember(Name = "image")]
        public string dockerImage { get; set; }

        [DataMember]
        public string jobType { get; set; }

        [DataMember]
        public string cmd { get; set; }

        [DataMember]
        public string jobtrainingtype { get; set; }

        [DataMember]
        public int numps { get; set; }

        [DataMember]
        public int numpsworker { get; set; }

        [DataMember]
        public int nummpiworker { get; set; }

        [DataMember]
        public string jobPath { get; set; }

        [DataMember]
        public string logDir { get; set; }

        [DataMember]
        public string interactivePort { get; set; }

        [DataMember]
        public string userName { get; set; }


        [DataMember]
        public string userId { get; set; }

        [DataMember]
        public string runningasroot { get; set; }

        [DataMember]
        public string containerUserId { get; set; }
        

        public override string ToString()
        {
            return JsonConvert.SerializeObject(this);
        }

        static public JobParams Deserialize(string str)
        {
            return JsonConvert.DeserializeObject<JobParams>(str) as JobParams;
        }
    }
}
