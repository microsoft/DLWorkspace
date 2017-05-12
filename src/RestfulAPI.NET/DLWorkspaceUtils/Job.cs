using System;
using System.Runtime.Serialization;
using Newtonsoft.Json;


namespace DLWorkspaceUtils
{
    [DataContract]
    public class Job
    {
        [DataMember]
        public string jobId { get; set; }

        [DataMember]
        public string jobName { get; set; }

        [DataMember]
        public string jobType { get; set; }

     
        [DataMember]
        public string userName { get; set; }

        [DataMember]
        public string jobStatus { get; set; }


        [DataMember]
        public string jobTime { get; set; }

        [DataMember]
        public string jobDescriptionPath { get; set; }

        [DataMember]
        public string jobDescription { get; set; }

        [DataMember]
        public string endpoints { get; set; }

        [DataMember]
        public JobParams jobParams { get; set; }

        [DataMember]
        public string errorMsg { get; set; }

        [DataMember]
        public string log { get; set; }

        public override string ToString()
        {
            return JsonConvert.SerializeObject(this);
        }

        static public Job Deserialize(string str)
        {
            return JsonConvert.DeserializeObject<Job>(str) as Job;
        }

    }
}
