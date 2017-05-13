using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Authentication.OpenIdConnect;
using Microsoft.AspNetCore.Http.Authentication;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Http; 
using System.Net.Http;
using System.Security.Principal;
using System.Security.Claims;

using WindowsAuth.models;
using WebPortal.Helper;
using WindowsAuth.Services;

// For more information on enabling MVC for empty projects, visit http://go.microsoft.com/fwlink/?LinkID=397860

namespace WindowsAuth.Controllers
{
    public class AccountController : Controller
    {
        // GET: /Account/Login
        [HttpGet("{scheme}")]
        public async Task Login(string scheme )
        {
            if (HttpContext.User == null || !HttpContext.User.Identity.IsAuthenticated)
            {
                await HttpContext.Authentication.ChallengeAsync(scheme, new AuthenticationProperties { RedirectUri = "/" });
            }
        }

        // Issue a challenge to send the user to AAD to sign in,
        // adding some additional data to the request which will be used in Startup.Auth.cs
        // The Tenant name here serves no functional purpose - it is only used to show how you
        // can collect additional information from the user during sign up.
        [HttpPost]
        [ValidateAntiForgeryToken]
        public async Task SignUp([Bind("ID", "Name", "AdminConsented")] Tenant tenant)
        {
            throw new Exception("Dead branch");
            await HttpContext.Authentication.ChallengeAsync(
                OpenIdConnectDefaults.AuthenticationScheme,
                new AuthenticationProperties(new Dictionary<string, string>
                {
                    { Constants.AdminConsentKey, tenant.AdminConsented.ToString() },
                    { Constants.TenantNameKey, tenant.Name }
                })
                { RedirectUri = "/" });
        }

        // GET: /Account/LogOff
        [HttpGet]
        public async Task<IActionResult> LogOff()
        {
            if (HttpContext.User.Identity.IsAuthenticated)
            {
                OpenIDAuthentication config;
                var scheme = Startup.GetAuthentication(HttpContext.Session.GetString("Username"), out config);
                await HttpContext.Authentication.SignOutAsync(scheme);
                await HttpContext.Authentication.SignOutAsync(CookieAuthenticationDefaults.AuthenticationScheme);
                return RedirectToAction("/");
            }
            else
                return RedirectToAction("/");
        }

        [HttpGet]
        public async Task EndSession()
        {
            if (User.Identity.IsAuthenticated)
            {
                IAzureAdTokenService tokenCache = (IAzureAdTokenService)HttpContext.RequestServices.GetService(typeof(IAzureAdTokenService));
                if ( !Object.ReferenceEquals(tokenCache, null))
                    tokenCache.Clear();
            }
            // If AAD sends a single sign-out message to the app, end the user's session, but don't redirect to AAD for sign out.
            await HttpContext.Authentication.SignOutAsync(CookieAuthenticationDefaults.AuthenticationScheme);
        }
    }
}
