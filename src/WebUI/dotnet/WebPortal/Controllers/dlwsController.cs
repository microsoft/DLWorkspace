using System;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Options;
using WindowsAuth.models;
using System.Net.Http;
using Microsoft.AspNetCore.Http;
using System.Runtime.Serialization;


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

        // GET api/dlws/op_str?params
        [HttpGet("{op}")]
        public async Task<string> Get(string op)
        {
            var ret = "invalid API call!";
            var url = "";

            if (!User.Identity.IsAuthenticated)
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
                    var result = GetTemplatesAsync();
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
            var json = "[";
            var templartFromDb = GetTemplatesString(database, databaseString);
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

        private async Task<string> GetTemplatesAsync()
        {
            string jsonString = "[";
            jsonString += "{\"Name\" : \"None\", \"Json\" : {}},";
            var master = GetTemplatesString(Startup.MasterDatabase, "Master");
            jsonString += await master;
            var currentCluster = HttpContext.Session.GetString("CurrentClusters");
            if (currentCluster != null && Startup.Database.ContainsKey(currentCluster))
            {
                var cluster = GetTemplatesString(Startup.Database[currentCluster], "CurrentCluster");
                jsonString += await cluster;
            }
            jsonString = jsonString.Substring(0, jsonString.Length - 1) + "]";
            return jsonString;
        }

        private static async Task<string> GetTemplatesString(ClusterContext templates, string databaseName)
        {
            try
            {
                var templatesString = "";
                var templatesList = templates.Template.ToAsyncEnumerable();
                await templatesList.ForEachAsync(entry =>
                {
                    var t = "{";
                    t += "\"Name\" : \"" + entry.Template + "\",";
                    t += "\"Username\" : \"" + entry.Username + "\",";
                    t += "\"Json\" : " + entry.Json + ",";
                    t += "\"Database\" : \"" + databaseName + "\"";
                    t += "},";
                    templatesString += t;
                });
                return templatesString;
            }
            catch (Exception e)
            {
                return "";
            }
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
                    var template = new TemplateEntry(templateParams.Name, username, templateParams.Json);
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
