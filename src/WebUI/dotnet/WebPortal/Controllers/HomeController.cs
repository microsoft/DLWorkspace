using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Options;
using WindowsAuth.models;
using System.Net.Http;
using System.Security.Claims;
using Newtonsoft.Json;
using System.Text;
using Microsoft.AspNetCore.Http;
using System.IO;


namespace WindowsAuth.Controllers
{
    public class HomeController : Controller
    {
        private readonly AppSettings _appSettings;



        public HomeController(IOptions<AppSettings> appSettings)
        {
            _appSettings = appSettings.Value;
        }




        public async Task<IActionResult> Index()
        {
            if (User.Identity.IsAuthenticated && !HttpContext.Session.Keys.Contains("uid"))
            {
                var url = "http://onenet40.redmond.corp.microsoft.com/domaininfo/GetUserId?userName=" + User.Identity.Name;
                using (var httpClient = new HttpClient())
                {
                    var response1 = await httpClient.GetAsync(url);
                    var content = await response1.Content.ReadAsStringAsync();
                    UserID userID = JsonConvert.DeserializeObject<UserID>(content.Trim()) as UserID;

                    userID.isAdmin = "false";
                    foreach (var adminGroupId in _appSettings.adminGroups)
                    {
                        if (userID.groups.Contains(adminGroupId))
                        {
                            userID.isAdmin = "true";
                        }
                    }

                    userID.isAuthorized = "false";
                    foreach (var authGroup in _appSettings.authorizedGroups)
                    {
                        if (userID.groups.Contains(authGroup))
                        {
                            userID.isAuthorized = "true";
                        }
                    }



                    HttpContext.Session.SetString("uid", userID.uid);

                    HttpContext.Session.SetString("gid", userID.gid);

                    HttpContext.Session.SetString("isAdmin", userID.isAdmin);

                    HttpContext.Session.SetString("isAuthorized", userID.isAuthorized);


                    if (userID.isAuthorized == "true")
                    {
                        url = _appSettings.restapi + "/AddUser?userName=" + User.Identity.Name + "&userId=" + userID.uid;
                        using (var httpClient1 = new HttpClient())
                        {
                            var response2 = await httpClient1.GetAsync(url);
                            var content1 = await response2.Content.ReadAsStringAsync();
                        }
                    }

                }





            }



                if (HttpContext.Session.Keys.Contains("isAuthorized"))
            {
                if (HttpContext.Session.GetString("isAuthorized") == "true")
                {
                    ViewData["isAuthorized"] = true;
                }
                else
                {
                    ViewData["isAuthorized"] = false;
                }
            }

            if (User.Identity.IsAuthenticated)
            {
                string username = User.Identity.Name;
                if (username.Contains("@"))
                {
                    username = username.Split(new char[] { '@' })[0];
                }
                if (username.Contains("/"))
                {
                    username = username.Split(new char[] { '/' })[1];
                }

                ViewData["username"] = username;

                ViewData["workPath"] = _appSettings.workFolderAccessPoint + username + "/";
                ViewData["dataPath"] = _appSettings.dataFolderAccessPoint;

            }
            return View();
        }
        public IActionResult JobSubmission()
        {
            if (!User.Identity.IsAuthenticated)
            {
                return RedirectToAction("Login", "Account", new { controller = "Account", action = "Login" });
            }

            if (!HttpContext.Session.Keys.Contains("isAuthorized") || HttpContext.Session.GetString("isAuthorized") != "true")
            {
                return RedirectToAction("Index", "Home");
            }

            string username = User.Identity.Name;
            if (username.Contains("@"))
            {
                username = username.Split(new char[] { '@' })[0];
            }
            if (username.Contains("/"))
            {
                username = username.Split(new char[] { '/' })[1];
            }

            ViewData["username"] = username;
            ViewData["workPath"] = _appSettings.workFolderAccessPoint+username+"/";
            ViewData["dataPath"] = _appSettings.dataFolderAccessPoint;

            ViewData["uid"] = HttpContext.Session.GetString("uid");
            ViewData["gid"] = HttpContext.Session.GetString("gid");

            ViewData["Message"] = "Your application description page.";
            //

            return View();
        }

        public IActionResult ViewJobs()
        {
            if (!User.Identity.IsAuthenticated)
            {
                return RedirectToAction("Login","Account",new { controller = "Account", action = "Login" });
            }

            if (!HttpContext.Session.Keys.Contains("isAuthorized") || HttpContext.Session.GetString("isAuthorized") != "true")
            {
                return RedirectToAction("Index", "Home");
            }


            ViewData["Message"] = "View and Manage Your Jobs.";

            return View();
        }

        public IActionResult JobDetail()
        {
            if (!User.Identity.IsAuthenticated)
            {
                return RedirectToAction("Login", "Account", new { controller = "Account", action = "Login" });
            }
            if (!HttpContext.Session.Keys.Contains("isAuthorized") || HttpContext.Session.GetString("isAuthorized") != "true")
            {
                return RedirectToAction("Index", "Home");
            }

            ViewData["Message"] = "View and Manage Your Jobs.";
            ViewData["jobid"] = HttpContext.Request.Query["jobId"];

            string username = User.Identity.Name;
            if (username.Contains("@"))
            {
                username = username.Split(new char[] { '@' })[0];
            }
            if (username.Contains("/"))
            {
                username = username.Split(new char[] { '/' })[1];
            }

            ViewData["username"] = username;
            ViewData["workPath"] = (_appSettings.workFolderAccessPoint + username + "/").Replace("file:","").Replace("\\","/");
            ViewData["jobPath"] = _appSettings.workFolderAccessPoint.Replace("file:","").Replace("\\","/");

            return View();
        }

        public IActionResult ViewCluster()
        {
            if (!User.Identity.IsAuthenticated)
            {
                return RedirectToAction("Login", "Account", new { controller = "Account", action = "Login" });
            }
            if (!HttpContext.Session.Keys.Contains("isAuthorized") || HttpContext.Session.GetString("isAuthorized") != "true")
            {
                return RedirectToAction("Index", "Home");
            }


            ViewData["Message"] = "Cluster Status.";

            return View();
        }


        public IActionResult About()
        {
            ViewData["Message"] = "Your application description page.";

            return View();
        }

        public IActionResult Contact()
        {
            ViewData["Message"] = "Your contact page.";

            return View();
        }

        public IActionResult Error()
        {
            return View();
        }
    }
}
