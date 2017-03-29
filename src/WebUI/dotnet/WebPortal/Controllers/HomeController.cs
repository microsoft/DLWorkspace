using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Options;
using WindowsAuth.models;
using System.Net.Http;

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
            return View();
        }
        public IActionResult JobSubmission()
        {
            if (!User.Identity.IsAuthenticated)
            {
                return RedirectToAction("Login", "Account", new { controller = "Account", action = "Login" });
            }

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

            ViewData["Message"] = "View and Manage Your Jobs.";

            return View();
        }

        public IActionResult JobDetail()
        {
            if (!User.Identity.IsAuthenticated)
            {
                return RedirectToAction("Login", "Account", new { controller = "Account", action = "Login" });
            }

            ViewData["Message"] = "View and Manage Your Jobs.";
            ViewData["jobid"] = HttpContext.Request.Query["jobId"];

            return View();
        }

        public IActionResult ViewCluster()
        {
            if (!User.Identity.IsAuthenticated)
            {
                return RedirectToAction("Login", "Account", new { controller = "Account", action = "Login" });
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
