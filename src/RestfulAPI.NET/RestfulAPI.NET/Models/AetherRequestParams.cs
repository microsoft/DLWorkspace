using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using System.Runtime.Serialization;
using Newtonsoft.Json;

namespace RestfulAPI.NET.Models
{
    [DataContract]
    public class MountPoint
    {
        [DataMember(Name = "Name")]
        public string Name { get; set; }

        [DataMember(Name = "Path")]
        public string Path { get; set; }

        [DataMember(Name = "ContainerPath")]
        public string ContainerPath { get; set; }


        public override string ToString()
        {
            return JsonConvert.SerializeObject(this);
        }

        static public MountPoint Deserialize(string str)
        {
            return JsonConvert.DeserializeObject<MountPoint>(str) as MountPoint;
        }
    }



        /// <summary>
        /// Query parameters for philly job submission HTTP call
        /// </summary>
        [DataContract]
    public class AetherRequestParams
    {
        [DataMember(Name = "toolType")]
        public string toolType { get; set; }

        /// <summary>
        /// Additional query parameter to differentiate AEther submission, "a" stands for AEther
        /// </summary>
        [DataMember(Name = "submitCode")]
        public string SubmitCode { get; set; }

        [DataMember(Name = "clusterId")]
        public string ClusterId { get; set; }

        [DataMember(Name = "JobName")]
        public string JobName { get; set; }

        [DataMember(Name = "userName")]
        public string UserName { get; set; }

        [DataMember(Name = "inputDir")]
        public string InputDirectory { get; set; }

        [DataMember(Name = "minGPUs")]
        public int MinGpus { get; set; }

        [DataMember(Name = "configFile")]
        public string ConfigFile { get; set; }

        [DataMember(Name = "buildId")]
        public string BuildId { get; set; }

        [DataMember(Name = "isDebug")]
        public bool IsDebug { get; set; }

        [DataMember(Name = "extraParams")]
        public string ExtraParams { get; set; }

        [DataMember(Name = "prevModelPath")]
        public string PreviousModelPath { get; set; }

        [DataMember(Name = "vcId")]
        public string VcId { get; set; }

        [DataMember(Name = "rackid")]
        public string RackId { get; set; }

        [DataMember(Name = "customDockerName")]
        public string CustomDockerName { get; set; }

        [DataMember(Name = "tag")]
        public string Tag { get; set; }

        [DataMember(Name = "oneProcessPerContainer")]
        public bool OneProcessPerContainer { get; set; }

        [DataMember(Name = "Inputs")]
        public List<MountPoint> Inputs { get; set; }

        [DataMember(Name = "Outputs")]
        public List<MountPoint> Outputs { get; set; }

        public override string ToString()
        {
            return JsonConvert.SerializeObject(this);
        }

        static public AetherRequestParams Deserialize(string str)
        {
            return JsonConvert.DeserializeObject<AetherRequestParams>(str) as AetherRequestParams;
        }
    }
}
