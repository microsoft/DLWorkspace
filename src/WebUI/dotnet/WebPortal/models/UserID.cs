using System;
using System.Collections.Generic;
using System.Linq;
using System.Runtime.Serialization;
using System.Threading.Tasks;

namespace WindowsAuth.models
{
    [DataContract]
    public class UserID
    {
        [DataMember(Name = "uid")]
        public string uid { get; set; }

        [DataMember(Name = "gid")]
        public string gid { get; set; }

        [DataMember(Name = "groups")]
        public List<string> groups { get; set; }

        public string isAdmin { get; set; }
        public string isAuthorized { get; set; }
    }
}
