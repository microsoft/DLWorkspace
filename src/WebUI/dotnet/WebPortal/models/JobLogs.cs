using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;

namespace WebPortal.models
{
    public class Reason
    {
        public string type { get; set; }
        public string reason { get; set; }
        public string index_uuid { get; set; }
        public string index { get; set; }
    }

    public class Failure
    {
        public int shard { get; set; }
        public string index { get; set; }
        public string node { get; set; }
        public Reason reason { get; set; }
    }

    public class Shards
    {
        public int total { get; set; }
        public int successful { get; set; }
        public int skipped { get; set; }
        public int failed { get; set; }
        public List<Failure> failures { get; set; }
    }

    public class Docker
    {
        public string container_id { get; set; }
    }

    public class Labels
    {
        public string jobName { get; set; }
        public string run { get; set; }
        public string userName { get; set; }
    }

    public class Kubernetes
    {
        public string container_name { get; set; }
        public string namespace_name { get; set; }
        public string pod_name { get; set; }
        public string pod_id { get; set; }
        public Labels labels { get; set; }
        public string host { get; set; }
        public string master_url { get; set; }
    }

    public class Source
    {
        public string log { get; set; }
        public string stream { get; set; }
        public string time { get; set; }
        public Docker docker { get; set; }
        public Kubernetes kubernetes { get; set; }
        public string tag { get; set; }
    }

    public class Hit
    {
        public string _index { get; set; }
        public string _type { get; set; }
        public string _id { get; set; }
        public object _score { get; set; }
        public Source _source { get; set; }
        public List<object> sort { get; set; }
    }

    public class Hits
    {
        public int total { get; set; }
        public object max_score { get; set; }
        public List<Hit> hits { get; set; }
    }

    public class JobLogs
    {
        public int took { get; set; }
        public bool timed_out { get; set; }
        public Shards _shards { get; set; }
        public Hits hits { get; set; }
    }
}
