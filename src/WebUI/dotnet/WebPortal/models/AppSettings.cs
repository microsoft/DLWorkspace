using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;

namespace WindowsAuth.models
{
    public class AppSettings
    {
        public string restapi { get; set; }
        public List<string> authorizedGroups { get; set; }
        public List<string> adminGroups { get; set; }
    }
}
