using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Options;
using WindowsAuth.models;
using System.Net.Http;
using System.Security.Principal;
using Microsoft.AspNetCore.Http;


// For more information on enabling Web API for empty projects, visit http://go.microsoft.com/fwlink/?LinkID=397860

namespace WindowsAuth.Controllers
{
    [Route("api/[controller]")]
    public class dlwsController : Controller
    {
        private readonly AppSettings _appSettings;
        private readonly FamilyModel _familyModel;

        public dlwsController(IOptions<AppSettings> appSettings, IOptions<FamilyModel> familyModel)
        {
            _appSettings = appSettings.Value;
	    _familyModel = familyModel.Value;
        }


        // GET api/dlws/op_str?params
        [HttpGet("{op}")]
        //public async Task<string> Get(string op, [FromQuery]string jobId)
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
                            url += System.Text.Encodings.Web.UrlEncoder.Default.Encode(item.Key) + "=" + System.Text.Encodings.Web.UrlEncoder.Default.Encode(item.Value) + "&";
                        }
                    }
                    url += "userName=" + HttpContext.Session.GetString("Email") + "&";
                    url += "userId=" + HttpContext.Session.GetString("uid") + "&";
                    if (HttpContext.Request.Query.ContainsKey("runningasroot") && HttpContext.Request.Query["runningasroot"] == "1")
                    {
                        url += "containerUserId=0&";
                    }

		    var familyToken = Guid.NewGuid();

                    var newKey = _familyModel.Families.TryAdd(familyToken, new FamilyModel.FamilyData
			    { ApiPath  = HttpContext.Session.GetString("Restapi")
			    , Email    = HttpContext.Session.GetString("Email")
			    , UID      = HttpContext.Session.GetString("uid") });
		    if(!newKey)
		    {
			ret = "Only 1 parent is allowed per family (maybe you tried to submit the same job on two threads?)";
		    }
                    url += $"familyToken={familyToken:N}&";
		    url += "isParent=1&";
                    break;
                case "GetClusterStatus":
                    url = restapi + "/GetClusterStatus?";
                    break;
                case "SaveTemplate":
                    if (HttpContext.Request.Query.ContainsKey("name"))
                    {
                        var message = SaveTemplateAsync(HttpContext.Request);
                        return "{ \"message\" : \"" + await message + "\"}";
                    }
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
	    if(!families.TryGetValue(familyToken, out familyData))
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
                            url += System.Text.Encodings.Web.UrlEncoder.Default.Encode(item.Key) + "=" + System.Text.Encodings.Web.UrlEncoder.Default.Encode(item.Value) + "&";
                        }
                    }
                    url += "userName=" + familyData.Email + "&";
                    url += "userId=" + familyData.UID + "&";
                    if (HttpContext.Request.Query.ContainsKey("runningasroot") && HttpContext.Request.Query["runningasroot"] == "1")
                    {
                        url += "containerUserId=0&";
                    }
		    if(HttpContext.Request.Query.ContainsKey("workPath"))
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
                        url = restapi + "/KillJob?jobId=" + HttpContext.Request.Query["jobId"] + "&userName=" + familyData.Email;
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


        private async Task<string> SaveTemplateAsync(HttpRequest httpQuery)
        {
            string templateName = httpQuery.Query["name"];
            string username = HttpContext.Session.GetString("Email");
            string json = httpQuery.Query["json"];

            var database = getDatabase(httpQuery);
            if (database == null)
            {
                return "Error: Could not save template to given database";
            }

            try
            {
                var a = database.Template.ToAsyncEnumerable();
                var other = a.Any(x => x.Template == templateName);
                if (await other)
                {
                    var temp = await a.First(x => x.Template == templateName);
                    if (temp.Username != username) return "Error: Template already exists in current location but belongs to someone else";
                    temp.Json = json;
                    database.SaveChangesAsync();
                    return "Succesfuly Edited Existing Template";
                }
                else
                {
                    var template = new TemplateEntry(templateName, username, json);
                    database.Template.Add(template);
                    database.SaveChangesAsync();
                    return "Succesfuly Saved New Template";
                }
            }
            catch (Exception e)
            {
                return "Error: Could not find Template Table in Cluster Database";
            }
        }

        private async Task<string> DeleteTemplateAsync(HttpRequest httpQuery)
        {
            string templateName = httpQuery.Query["name"];
            var isAdmin = HttpContext.Session.GetString("isAdmin").Equals("true");
            string username = HttpContext.Session.GetString("Email");

            var database = getDatabase(httpQuery);
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
                    database.SaveChangesAsync();
                    return "Job Successfully Deleted!";
                }
            }
            catch (Exception e)
            {
                return "Error: Could not find job to be deleted";
            }

            return "Error: Could not delete job";
        }

        private ClusterContext getDatabase(HttpRequest httpQuery)
        {
            string location = httpQuery.Query["location"];
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
            string jsonString = "{\"templates\" : [ ";
            jsonString += "{\"name\" : \"None\", \"template\" : {}},";
            var master = GetTemplatesFromDb(Startup.MasterDatabase, "Master");
            jsonString += await master;
            var currentCluster = HttpContext.Session.GetString("CurrentClusters");
            if (currentCluster != null && Startup.Database.ContainsKey(currentCluster))
            {
                var cluster = GetTemplatesFromDb(Startup.Database[currentCluster], "CurrentCluster");
                jsonString += await cluster;
            }

            jsonString = jsonString.Substring(0, jsonString.Length - 1) + "]}";
            return jsonString;
        }

        private async Task<string> GetTemplatesFromDb(ClusterContext templates, string databaseName)
        {
            try
            {
                string templatesString = "";
                if(templates.Template.Count() <= 0) return "";
                var templatesList = templates.Template.ToAsyncEnumerable();
                await templatesList.ForEachAsync(entry =>
                {
                    string t = "{";
                    t += "\"name\" : \"" + entry.Template + "\",";
                    t += "\"template\" : " + entry.Json + ",";
                    t += "\"location\" : \"" + databaseName + "\"";
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

        //// POST api/values
        //[HttpPost]
        //public void Post([FromBody]string value)
        //{
        //}

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
