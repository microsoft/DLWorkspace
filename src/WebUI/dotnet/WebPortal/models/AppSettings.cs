using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;

namespace WindowsAuth.models
{
    public class AppSettings
    {
        // RestAPI, workFolderAccess, dataFolderAccess is cluster dependant, as the webUI will support multi-cluster, 
        // the information will be stored in session. 
        // public string restapi { get; set; }
        // public string workFolderAccessPoint { get; set; }
        // public string dataFolderAccessPoint { get; set; }
        // public List<string> authorizedGroups { get; set; }
        // public List<string> adminGroups { get; set; }
    }
}
