using System;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Options;
using WindowsAuth.models;
using System.Net.Http;
using Microsoft.AspNetCore.Http;
using System.Runtime.Serialization;
using Newtonsoft.Json;
using System.Collections.Generic;

// For more information on enabling Web API for empty projects, visit http://go.microsoft.com/fwlink/?LinkID=397860

namespace WindowsAuth.Controllers
{
    [Route("api/[controller]")]
    public class dlwsController : Controller
    {
        [DataContract]
        public class TemplateParams
        {
            [DataMember(Name = "Name")]
            public string Name { get; set; }

            [DataMember(Name = "Username")]
            public string Username { get; set; }

            [DataMember(Name = "Json")]
            public string Json { get; set; }

            [DataMember(Name = "Database")]
            public string Database { get; set; }
        }
        
        private readonly AppSettings _appSettings;
        private readonly FamilyModel _familyModel;

        public dlwsController(IOptions<AppSettings> appSettings, IOptions<FamilyModel> familyModel)
        {
            _appSettings = appSettings.Value;
            _familyModel = familyModel.Value;
        }

        // this function should be moved to a shared util-class
        private string ParseToUsername(string email)
        {
            string username = email;
            if (username.Contains("@"))
            {
                username = username.Split('@')[0];
            }
            if (username.Contains("/"))
            {
                username = username.Split('/')[1];
            }
            return username;
        }

        [HttpGet("GetMountPoints")]
        public async Task<IActionResult> GetMountPoints()
        {
            var currentCluster = HttpContext.Session.GetString("CurrentClusters");
            var currentUsername = HttpContext.Session.GetString("Username");
            if (String.IsNullOrEmpty(currentCluster) || !Startup.Clusters.ContainsKey(currentCluster) )
            {
                return Json(new { mountdescription = "{}", mountpoints = "{}", username= currentUsername,
                                mounthomefolder = false,
                                deploymounts = "[]"} );
            }
            else
            {
                var curCluster = Startup.Clusters[currentCluster];
                return Json(new { mountdescription = curCluster.MountDescription,
                                    mountpoints = curCluster.MountPoints,
                                    username = currentUsername,
                                    mounthomefolder = curCluster.MountHomeFolder, 
                                    deploymounts = curCluster.DeployMounts
                                    });
            }
        }


        // GET api/dlws/op_str?params
        [HttpGet("{op}")]
        public async Task<string> Get(string op)
        {
            var ret = "invalid API call!";
            var url = "";

            var passwdLogin = false;

            if (HttpContext.Request.Query.ContainsKey("Email") && HttpContext.Request.Query.ContainsKey("Key"))
            {
                
                var databases = Startup.Database;
                var tasks = new List<Task<UserEntry>>();
                var lst = new List<string>();
                string email = HttpContext.Request.Query["Email"];
                string password = HttpContext.Request.Query["Key"];
                
                foreach (var pair in databases)
                {
                    var clusterName = pair.Key;
                    var db = pair.Value;


                    var priorEntrys = db.User.Where(b => b.Email == email).Where(b => b.Password == password).ToAsyncEnumerable();

                    await priorEntrys.ForEachAsync(userEntry =>
                    {
                        // find the first database where the user has access permission. 
                        if (!passwdLogin)
                        {
                            HttpContext.Session.SetString("Email", userEntry.Alias);
                            var username = ParseToUsername(userEntry.Alias);
                            HttpContext.Session.SetString("Username", username);
                            HttpContext.Session.SetString("uid", userEntry.uid);
                            HttpContext.Session.SetString("gid", userEntry.gid);
                            HttpContext.Session.SetString("isAdmin", userEntry.isAdmin);
                            HttpContext.Session.SetString("isAuthorized", userEntry.isAuthorized);
                            var clusterInfo = Startup.Clusters[clusterName];
                            HttpContext.Session.SetString("Restapi", clusterInfo.Restapi);
                            HttpContext.Session.SetString("WorkFolderAccessPoint", clusterInfo.WorkFolderAccessPoint);
                            HttpContext.Session.SetString("DataFolderAccessPoint", clusterInfo.DataFolderAccessPoint);
                            passwdLogin = userEntry.isAuthorized == "true";
                        }
                    }
                    );
                }
                
            }


            if (!User.Identity.IsAuthenticated && !passwdLogin)
            {
                ret = "Unauthorized User, Please login!";
                return ret;
            }

            ViewData["Username"] = HttpContext.Session.GetString("Username");
            var restapi = HttpContext.Session.GetString("Restapi");

            switch (op)
            {
                case "ListJobs":
                    url = restapi + "/ListJobs?userName=" + HttpContext.Session.GetString("Email");
                    break;
                case "ListAllJobs":
                    if (HttpContext.Session.GetString("isAdmin").Equals("true"))
                    {
                        url = restapi + "/ListJobs?userName=all";
                    }
                    break;
                case "KillJob":
                    if (HttpContext.Request.Query.ContainsKey("jobId"))
                    {
                        url = restapi + "/KillJob?jobId=" + HttpContext.Request.Query["jobId"] + "&userName=" + HttpContext.Session.GetString("Email");
                    }
                    break;
                case "ApproveJob":
                    if (HttpContext.Request.Query.ContainsKey("jobId") && HttpContext.Session.GetString("isAdmin").Equals("true"))
                    {
                        url = restapi + "/ApproveJob?jobId=" + HttpContext.Request.Query["jobId"] + "&userName=" + HttpContext.Session.GetString("Email");
                    }
                    break;
                case "JobDetail":
                    if (HttpContext.Request.Query.ContainsKey("jobId"))
                    {
                        url = restapi + "/GetJobDetail?jobId=" + HttpContext.Request.Query["jobId"];
                    }
                    break;
                case "SubmitJob":
                    url = restapi + "/SubmitJob?";
                    foreach (var item in HttpContext.Request.Query)
                    {
                        //security check, user cannot append userName to the request url
                        if (item.Key.ToLower() != "username")
                        {
                            url += System.Text.Encodings.Web.UrlEncoder.Default.Encode(item.Key) + "=" +
                                   System.Text.Encodings.Web.UrlEncoder.Default.Encode(item.Value) + "&";
                        }
                    }
                    url += "userName=" + HttpContext.Session.GetString("Email") + "&";
                    url += "userId=" + HttpContext.Session.GetString("uid") + "&";
                    if (HttpContext.Request.Query.ContainsKey("runningasroot") &&
                        HttpContext.Request.Query["runningasroot"] == "1")
                    {
                        url += "containerUserId=0&";
                    }

                    var familyToken = Guid.NewGuid();

                    var newKey = _familyModel.Families.TryAdd(familyToken, new FamilyModel.FamilyData
                    {
                        ApiPath = HttpContext.Session.GetString("Restapi"),
                        Email = HttpContext.Session.GetString("Email"),
                        UID = HttpContext.Session.GetString("uid")
                    });
                    if (!newKey)
                    {
                        ret = "Only 1 parent is allowed per family (maybe you tried to submit the same job on two threads?)";
                    }
                    url += $"familyToken={familyToken:N}&";
                    url += "isParent=1&";
                    break;
                case "GetClusterStatus":
                    url = restapi + "/GetClusterStatus?";
                    break;
                case "DeleteTemplate":
                    if (HttpContext.Request.Query.ContainsKey("name"))
                    {
                        var message = DeleteTemplateAsync(HttpContext.Request);
                        return "{ \"message\" : \"" + await message + "\"}";
                    }
                    break;
                case "GetTemplates":
                    var result = GetTemplatesAsync(HttpContext.Request.Query["type"]);
                    return await result;
                    break;
                case "GetDatabase":
                    var databaseJson = DownloadDatabase(HttpContext.Request);
                    return await databaseJson;
                    break;
                case "RunCommand":
                    if (HttpContext.Request.Query.ContainsKey("jobId") && HttpContext.Request.Query.ContainsKey("command"))
                    {
                        url = restapi + "/AddCommand?jobId=" + HttpContext.Request.Query["jobId"] + "&command=" + HttpContext.Request.Query["command"];
                    }
                    break;
                case "GetCommands":
                    if (HttpContext.Request.Query.ContainsKey("jobId"))
                    {
                        url = restapi + "/GetCommands?jobId=" + HttpContext.Request.Query["jobId"];
                    }
                    break;
            }

            if (url != "")
            {
                using (var httpClient = new HttpClient())
                {
                    var response1 = await httpClient.GetAsync(url);
                    var content = await response1.Content.ReadAsStringAsync();
                    ret = content;
                }
            }
            return ret;
        }

        // GET api/dlws/child/op_str?params
        [HttpGet("child/{op}")]
        public async Task<string> ChildReq(string op)
        {
            var ret = "invalid API call!";
            var url = "";
            var familyToken = new Guid(HttpContext.Request.Query["familyToken"]);
            var families = _familyModel.Families;
            FamilyModel.FamilyData familyData;
            if (!families.TryGetValue(familyToken, out familyData))
            {
                ret = "provided family token was invalid";
                return ret;
            }
            var restapi = familyData.ApiPath;

            switch (op)
            {
                case "SubmitJob":
                    url = restapi + "/SubmitJob?";
                    foreach (var item in HttpContext.Request.Query)
                    {
                        //security check, user cannot append userName to the request url
                        if (item.Key.ToLower() != "username")
                        {
                            url += System.Text.Encodings.Web.UrlEncoder.Default.Encode(item.Key) + "=" +
                                   System.Text.Encodings.Web.UrlEncoder.Default.Encode(item.Value) + "&";
                        }
                    }
                    url += "userName=" + familyData.Email + "&";
                    url += "userId=" + familyData.UID + "&";
                    if (HttpContext.Request.Query.ContainsKey("runningasroot") &&
                        HttpContext.Request.Query["runningasroot"] == "1")
                    {
                        url += "containerUserId=0&";
                    }
                    if (HttpContext.Request.Query.ContainsKey("workPath"))
                    {
                        url += "workPath=" + HttpContext.Request.Query["workPath"] + "&";
                    }
                    else
                    {
                        url += "workPath=" + familyData.Email + "&";
                    }
                    url += "isParent=0&";
                    break;
                case "KillJob":
                    if (HttpContext.Request.Query.ContainsKey("jobId"))
                    {
                        url = restapi + "/KillJob?jobId=" + HttpContext.Request.Query["jobId"] + "&userName=" +
                              familyData.Email;
                    }
                    break;
                case "JobDetail":
                    if (HttpContext.Request.Query.ContainsKey("jobId"))
                    {
                        url = restapi + "/GetJobDetail?jobId=" + HttpContext.Request.Query["jobId"];
                    }
                    break;
            }

            if (url != "")
            {
                using (var httpClient = new HttpClient())
                {
                    var response1 = await httpClient.GetAsync(url);
                    var content = await response1.Content.ReadAsStringAsync();
                    ret = content;
                }
            }
            return ret;
        }
        
        // POST api/dlws/submit
        [HttpPost("submit")]
        public async Task<string> PostAsync(TemplateParams templateParams)
        {
            var message = SaveTemplateAsync(templateParams);
            return "{ \"message\" : \"" + await message + "\"}";
        }
        
        //Helper Methods
        private async Task<string> DownloadDatabase(HttpRequest httpContextRequest)
        {
            string databaseString = httpContextRequest.Query["location"];
            var database = GetDatabaseFromString(databaseString);
            if (database.Template.Count() == 0) return "[]";
            var json = "[";
            var templartFromDb = GetTemplatesString(database, databaseString, "all");
            json += await templartFromDb;
            return json.Substring(0, json.Length - 1) + "]";
        }        
      
        private async Task<string> DeleteTemplateAsync(HttpRequest httpQuery)
        {
            string templateName = httpQuery.Query["name"];
            var isAdmin = HttpContext.Session.GetString("isAdmin").Equals("true");
            string username = HttpContext.Session.GetString("Email");
            string databaseString = httpQuery.Query["location"];

            var database = GetDatabaseFromString(databaseString);
            if (database == null)
            {
                return "Error: Could not delete template from given database";
            }
            try
            {
                var template = await database.Template.ToAsyncEnumerable().First(t => t.Template == templateName);
                if (isAdmin || template.Username == username)
                {
                    database.Template.Remove(template);
                    await database.SaveChangesAsync();
                    return "Job Successfully Deleted!";
                }
            }
            catch (Exception e)
            {
                return "Error: Could not find job to be deleted";
            }

            return "Error: Could not delete job";
        }

        private ClusterContext GetDatabaseFromString(string location)
        { 
            if (location == "Master")
            {
                if (HttpContext.Session.GetString("isAdmin").Equals("true"))
                {
                    return Startup.MasterDatabase;
                }
            }
            else
            {
                var currentCluster = HttpContext.Session.GetString("CurrentClusters");
                if (Startup.Database.ContainsKey(currentCluster))
                {
                    return Startup.Database[currentCluster];
                }
            }
            return null;
        }

        private async Task<string> GetTemplatesAsync(string type)
        {
            string jsonString = "[";
            jsonString += "{\"Name\" : \"None\", \"Json\" : \"{}\"},";
            var master = GetTemplatesString(Startup.MasterDatabase, "Master", type);
            jsonString += await master;
            var currentCluster = HttpContext.Session.GetString("CurrentClusters");
            if (currentCluster != null && Startup.Database.ContainsKey(currentCluster))
            {
                var cluster = GetTemplatesString(Startup.Database[currentCluster], "CurrentCluster", type);
                jsonString += await cluster;
            }
            jsonString = jsonString.Substring(0, jsonString.Length - 1) + "]";
            return jsonString;
        }

        private static async Task<string> GetTemplatesString(ClusterContext templates, string databaseName, string type)
        {
            try
            {
                var templatesString = "";
                var templatesList = templates.Template.ToAsyncEnumerable();
                await templatesList.ForEachAsync(entry =>
                {
                    if (type == "all" || entry.Type == type)
                    {
                        var t = "{";
                        t += "\"Name\" : \"" + entry.Template + "\",";
                        t += "\"Username\" : \"" + entry.Username + "\",";
                        t += "\"Json\" : " + JsonConvert.SerializeObject(entry.Json) + ",";
                        t += "\"Database\" : \"" + databaseName + "\"";
                        t += "},";
                        templatesString += t;
                    }
                });
                return templatesString;
            }
            catch (Exception e)
            {
                return "";
            }
        }

        private static async Task<string> GetCommandTemplates()
        {
            var jsonString = "[";
            jsonString += "{\"Name\" : \"None\", \"Command\" : \"\"},";
            var templatesList = Startup.MasterDatabase.Template.ToAsyncEnumerable();
            await templatesList.ForEachAsync(entry =>
            {
                if (!entry.Json.StartsWith("{"))
                {
                    var t = "{";
                    t += "\"Name\" : \"" + entry.Template + "\",";
                    t += "\"Command\" : \"" + entry.Json + "\"";
                    t += "},";
                    jsonString += t;
                }
            });
            jsonString = jsonString.Substring(0, jsonString.Length - 1) + "]";
            return jsonString;
        }

        private async Task<string> SaveTemplateAsync(TemplateParams templateParams)
        {
            var database = GetDatabaseFromString(templateParams.Database);
            if (database == null)
            {
                return "Error: Could not save template to given database";
            }
            var username = templateParams.Username ?? HttpContext.Session.GetString("Email");

            try
            {
                var a = database.Template.ToAsyncEnumerable();
                var other = a.Any(x => x.Template == templateParams.Name);
                if (await other)
                {
                    var temp = await a.First(x => x.Template == templateParams.Name);
                    if (temp.Username != username) return "Error: Template already exists in current location but belongs to someone else";
                    temp.Json = templateParams.Json;
                    await database.SaveChangesAsync();
                    return "Succesfuly Edited Existing Template";
                }
                else
                {
                    var template = new TemplateEntry(templateParams.Name, username, templateParams.Json, "job");
                    database.Template.Add(template);
                    await database.SaveChangesAsync();
                    return "Succesfuly Saved New Template";
                }
            }
            catch (Exception e)
            {
                return "Error: Could not find Template Table in Cluster Database";
            }
        }
        
        //// PUT api/values/5
        //[HttpPut("{id}")]
        //public void Put(int id, [FromBody]string value)
        //{
        //}

        //// DELETE api/values/5
        //[HttpDelete("{id}")]
        //public void Delete(int id)
        //{
        //}
    }
}
