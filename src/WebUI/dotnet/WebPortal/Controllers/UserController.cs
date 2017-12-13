using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.AspNetCore;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using WindowsAuth.models;
using WindowsAuth.Services;
using Microsoft.AspNetCore.Http;

namespace WindowsAuth.Controllers
{
    public class UserController : Controller
    {
        private readonly AppSettings _appSettings;
        private readonly ILogger _logger;
        private IAzureAdTokenService _tokenCache;


        public UserController(IOptions<AppSettings> appSettings, IAzureAdTokenService tokenCache, ILoggerFactory logger)
        {
            _appSettings = appSettings.Value;
            _tokenCache = tokenCache;
            _logger = logger.CreateLogger("UserController");
        }


    }
}
