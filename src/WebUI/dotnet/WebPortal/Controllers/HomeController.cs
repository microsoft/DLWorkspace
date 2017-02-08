using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Options;
using WebPortal.models;

namespace WebPortal.Controllers
{
    public class HomeController : Controller
    {
        private readonly AppSettings _appSettings;


        public HomeController(IOptions<AppSettings> appSettings)
        {
            _appSettings = appSettings.Value;
        }

        public IActionResult Index()
        {
            return View();
        }
        public IActionResult JobSubmission()
        {
            ViewData["Message"] = "Your application description page.";
            ViewData["restapi"] = _appSettings.restapi;

            return View();
        }

        public IActionResult ViewJobs()
        {
            ViewData["Message"] = "View and Manage Your Jobs.";
            ViewData["restapi"] = _appSettings.restapi;

            return View();
        }

        public IActionResult JobDetail()
        {
            ViewData["Message"] = "View and Manage Your Jobs.";
            ViewData["jobid"] = HttpContext.Request.Query["jobId"];
            ViewData["restapi"] = _appSettings.restapi;


            return View();
        }

        public IActionResult About()
        {
            ViewData["Message"] = "Your application description page.";
            ViewData["restapi"] = _appSettings.restapi;

            return View();
        }

        public IActionResult Contact()
        {
            ViewData["Message"] = "Your contact page.";
            ViewData["restapi"] = _appSettings.restapi;

            return View();
        }

        public IActionResult Error()
        {
            return View();
        }
    }
}
