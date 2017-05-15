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


        public dlwsController(IOptions<AppSettings> appSettings)
        {
            _appSettings = appSettings.Value;
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
            if (op == "ListJobs")
            {
                url = _appSettings.restapi + "/ListJobs?userName="+HttpContext.Session.GetString("Username");
            }
            else if (op == "KillJob" && HttpContext.Request.Query.ContainsKey("jobId"))
            {
                url = _appSettings.restapi + "/KillJob?jobId=" + HttpContext.Request.Query["jobId"]+"&userName="+ HttpContext.Session.GetString("Username");
            }
            else if (op == "JobDetail" && HttpContext.Request.Query.ContainsKey("jobId"))
            {
                url = _appSettings.restapi + "/GetJobDetail?jobId=" + HttpContext.Request.Query["jobId"];
            }
            else if (op == "SubmitJob")
            {
                url = _appSettings.restapi + "/SubmitJob?";
                foreach (var item in HttpContext.Request.Query)
                {
                    //security check, user cannot append userName to the request url
                    if (item.Key.ToLower() != "username")
                    {
                        url += System.Text.Encodings.Web.UrlEncoder.Default.Encode(item.Key) + "=" + System.Text.Encodings.Web.UrlEncoder.Default.Encode(item.Value) + "&";
                    }
                }
                url += "userName=" + HttpContext.Session.GetString("Username") + "&";
                url += "userId=" + HttpContext.Session.GetString("uid") + "&";
                if (HttpContext.Request.Query.ContainsKey("runningasroot") && HttpContext.Request.Query["runningasroot"] == "1")
                {
                    url += "containerUserId=0&";
                }
            }
            else if (op == "GetClusterStatus")
            {
                url = _appSettings.restapi + "/GetClusterStatus?";
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
