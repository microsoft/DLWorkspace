using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Authentication.OpenIdConnect;
using Microsoft.AspNetCore.Authentication.MicrosoftAccount;
using Microsoft.AspNetCore.Http.Authentication;
using Microsoft.AspNetCore.Mvc;
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
        private string _authentication = null; 
        // GET: /Account/Login
        [HttpGet]
        public async Task Login_OpenId()
        {
            if (HttpContext.User == null || !HttpContext.User.Identity.IsAuthenticated)
            {
                await HttpContext.Authentication.ChallengeAsync(OpenIdConnectDefaults.AuthenticationScheme, new AuthenticationProperties { RedirectUri = "/" });
            }
        }

        public async Task Login_MicrosoftAccount()
        {
            if (HttpContext.User == null || !HttpContext.User.Identity.IsAuthenticated)
            { 
                await HttpContext.Authentication.ChallengeAsync(MicrosoftAccountDefaults.AuthenticationScheme, new AuthenticationProperties { RedirectUri = "/" });
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
            await HttpContext.Authentication.ChallengeAsync(
                OpenIdConnectDefaults.AuthenticationScheme,
                new AuthenticationProperties(new Dictionary<string, string>
                {
                    { Constants.AdminConsentKey, tenant.AdminConsented.ToString() },
                    { Constants.TenantNameKey, tenant.Name }
                })
                { RedirectUri = "/" });
        }

        public bool isOpenId()
        {
            if (String.IsNullOrEmpty(HttpContext.User.Identity.Name))
            {
                return false;
            }
            else
            {
                if (HttpContext.User.Identity.Name.Contains("@microsoft.com"))
                    return true;
                else
                    return false; 
            }
        }

        public bool isMicrosoftAccount()
        {
            if (String.IsNullOrEmpty(HttpContext.User.Identity.Name))
            {
                return false;
            }
            else
            {
                if (HttpContext.User.Identity.Name.Contains("@live.com") ||
                    HttpContext.User.Identity.Name.Contains("@outlook.com") ||
                    HttpContext.User.Identity.Name.Contains("@hotmail.com"))
                    return true;
                else
                    return false;
            }
        }

        // GET: /Account/LogOff
        [HttpGet]
        public async Task LogOff()
        {
            if (HttpContext.User.Identity.IsAuthenticated)
            {
                if (isOpenId())
                {
                    await HttpContext.Authentication.SignOutAsync(OpenIdConnectDefaults.AuthenticationScheme);
                }
                else if (isMicrosoftAccount())
                {
                    await HttpContext.Authentication.SignOutAsync(MicrosoftAccountDefaults.AuthenticationScheme);
                }
                await HttpContext.Authentication.SignOutAsync(CookieAuthenticationDefaults.AuthenticationScheme);
            }
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
