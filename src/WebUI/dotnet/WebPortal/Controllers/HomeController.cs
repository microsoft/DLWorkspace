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

using System.Reflection;
using Microsoft.Extensions.Logging;


using Microsoft.AspNetCore.Authentication.OpenIdConnect;
using Microsoft.IdentityModel.Clients.ActiveDirectory;
using Microsoft.IdentityModel.Clients;
using Microsoft.Practices.EnterpriseLibrary.TransientFaultHandling;
using Newtonsoft.Json.Linq;
using System.Net;
using System.Globalization;
using WindowsAuth;


namespace WindowsAuth.Controllers
{
    public class HomeController : Controller
    {
        private readonly AppSettings _appSettings;
        private readonly ILogger _logger;


        public HomeController(IOptions<AppSettings> appSettings, ILoggerFactory logger)
        {
            _appSettings = appSettings.Value;
            _logger = logger.CreateLogger("HomeController");
        }

        private async Task<bool> AuthenticateByServer(string connectURL )
        {
            string url = String.Format(CultureInfo.InvariantCulture, connectURL, User.Identity.Name); 
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
            return true; 

        }

        // TODO: This is sample code that needs validation from the WAAD team!
        // based on existing detection strategies
        public class AdalDetectionStrategy : ITransientErrorDetectionStrategy
        {
            private static readonly WebExceptionStatus[] webExceptionStatus =
                new[]
                {
                WebExceptionStatus.ConnectionClosed,
                WebExceptionStatus.Timeout,
                WebExceptionStatus.RequestCanceled
                };

            private static readonly HttpStatusCode[] httpStatusCodes =
                new[]
                {
                HttpStatusCode.InternalServerError,
                HttpStatusCode.GatewayTimeout,
                HttpStatusCode.ServiceUnavailable,
                HttpStatusCode.RequestTimeout
                };

            public bool IsTransient(Exception ex)
            {
                var adalException = ex as AdalException;
                if (adalException == null)
                {
                    return false;
                }

                if (adalException.ErrorCode == AdalError.ServiceUnavailable)
                {
                    return true;
                }

                var innerWebException = adalException.InnerException as WebException;
                if (innerWebException != null)
                {
                    if (webExceptionStatus.Contains(innerWebException.Status))
                    {
                        return true;
                    }

                    if (innerWebException.Status == WebExceptionStatus.ProtocolError)
                    {
                        var response = innerWebException.Response as HttpWebResponse;
                        return response != null && httpStatusCodes.Contains(response.StatusCode);
                    }
                }

                return false;
            }
        }

        

        private async Task<AuthenticationResult> AcquireCredentialAsyncForApplication()
        {
            string aadInstance = Startup.Configuration["AzureAd:AadInstance"];
            string TenantName = Startup.Configuration["AzureAd:Tenant"];
            // string TenantName = Startup.Configuration["AzureAd:AltTenant"];
            string clientId = Startup.Configuration["AzureAd:ClientId"];
            string clientSecret = Startup.Configuration["AzureAd:ClientSecret"];
            // string clientId = Startup.Configuration["AzureAd:AltClientId"];
            // string clientSecret = Startup.Configuration["AzureAd:AltClientSecret"];
            string authority = String.Format(CultureInfo.InvariantCulture, aadInstance, TenantName);
            // var authority = string.Format(@"https://accounts.accesscontrol.windows.net/{0}", tenantID);
            _logger.LogInformation("Authority is {0}", authority);
            AuthenticationContext _authContext = new AuthenticationContext(authority, false);
            string objectId = Startup.Configuration["AzureAd:ObjectId"];
            string appIDUri = Startup.Configuration["AzureAd:AppIDUri"];
            _logger.LogInformation("Credential is {0}:{1}", clientId, clientSecret);
            ClientCredential _cred = new ClientCredential(clientId, clientSecret);
            // ClientCredential _cred = new ClientCredential ( clientId+"@"+tenantID, clientSecret);
            string resourceURL = Startup.Configuration["AzureAd:ResourceURL"];
            // var resourceURL = string.Format(@"00000002-0000-0000-c000-000000000000/graph.windows.net@{0}", tenantID);
            _logger.LogInformation("URL : {0}", resourceURL);
            var policy = new RetryPolicy<AdalDetectionStrategy>(new ExponentialBackoff(retryCount: 5, minBackoff: TimeSpan.FromSeconds(0),
                                                             maxBackoff: TimeSpan.FromSeconds(60),
                                                             deltaBackoff: TimeSpan.FromSeconds(2)));
            var _assertionCredential = await policy.ExecuteAsync(() => _authContext.AcquireTokenAsync(resourceURL, _cred));
            // string authHeader = _assertionCredential.CreateAuthorizationHeader(); 
            return _assertionCredential;
        }


        private async Task<bool> AuthenticateByAAD()
        {
            bool ret = true;
            var id = User.Identity as ClaimsIdentity;
            string userObjectID = null;
            if (id != null)
            {

                string username = User.Identity.Name;
                string tenantID = null;
                string upn = null;
                string endpoint = null; 

                _logger.LogInformation("Number of Claims owned by User {0} : {1} ", username, id.Claims.Count());
                foreach (var claim in id.Claims)
                {
                    var examine = claim.Issuer;

                    _logger.LogInformation("User {0} has claim {1}", username, claim);
                    Type claimType = claim.GetType();
                    PropertyInfo[] properties = claimType.GetProperties();
                    foreach (var prp in properties)
                    {
                        var value = prp.GetValue(claim);
                        _logger.LogInformation("Property {0} is {1}", prp.Name, value);
                    }

                    if ( claim.Type == id.RoleClaimType)
                    {
                    }

                    if (claim.Type.IndexOf("_claim_sources")>=0 )
                    {
                        string json = claim.Value;
                        var dic = JObject.Parse(json);
                        try
                        {
                            foreach (var src1 in dic["src1"])
                            {
                                foreach (var ep in src1)
                                { 
                                    endpoint = ep.ToString();
                                }
                            }
                        }
                        catch (Exception e)
                        { }
                    }
                    // http://schemas.microsoft.com/identity/claims/objectidentifier
                    if (claim.Type.IndexOf("identity/claims/objectidentifier")>=0 )
                    {
                        userObjectID = claim.Value;
                    }
                    // http://schemas.xmlsoap.org/ws/2005/05/identity/claims/upn
                    if (claim.Type.IndexOf( "identity/claims/upn") >=0 )
                    {
                        upn = claim.Value;
                    }
                    // http://schemas.microsoft.com/ws/2012/10/identity/claims/tenantid
                    if (claim.Type.IndexOf ( "identity/claims/tenantid") >=0 )
                    {
                        tenantID = claim.Value;
                    }
                }

                if ( !String.IsNullOrEmpty(tenantID) && !String.IsNullOrEmpty(upn ) && !String.IsNullOrEmpty(endpoint))
                {
                    var _assertionCredential = await AcquireCredentialAsyncForApplication();
                    string TenantName = Startup.Configuration["AzureAd:Tenant"];
                    string apiVersion = Startup.Configuration["AzureAd:GraphApiVersion"];
                    // string requestURL = string.Format(@"https://graph.windows.net/{0}/users/{1}/memberOf?api-version={2}", TenantName, userObjectID, apiVersion);
                    // string requestURL = string.Format(@"https://graph.windows.net/myorganization/groups/?api-version={1}", TenantName, apiVersion);
                    // string requestURL = string.Format(@"http://www.google.com");
                    // string requestURL = endpoint; 
                    // string requestURL = @"https://graph.microsoft.com/v1.0/groups/ad53e8c9-3627-4a83-979e-63a1756d9a9f";
                    string requestURL = @"https://graph.microsoft.com/v1.0/me";
                    HttpWebRequest webRequest = WebRequest.Create(requestURL) as HttpWebRequest;
                    webRequest.Method = "Get";
                    string token = _assertionCredential.AccessToken;
                    string authHeader = _assertionCredential.CreateAuthorizationHeader();
                    webRequest.Headers["Authorization"] = authHeader;
                    webRequest.Headers["access-control-allow-origin"] = "*";
                    webRequest.Headers["access-control-expose-headers"] = "ETag, Location, Preference-Applied, Content-Range, request-id, client-request-id";

                    
                    // webRequest.Headers["x-ms-dirapi-data-contract-version"] = "0.8";
                    string jsonText=null;
                    var content = new MemoryStream(); 
                    using (var httpResponse = await webRequest.GetResponseAsync())
                    {
                        using (var responseStream = httpResponse.GetResponseStream())
                        {
                            await responseStream.CopyToAsync(content);
                        }
                    }
                    jsonText = Encoding.UTF7.GetString(content.ToArray());
                    // string resourceURL = Startup.Configuration["AzureAd:ResourceURL"];
                    // var servicePointUri = new Uri(resourceURL);
                    // System.Uri serviceRoot = new Uri(servicePointUri, tenantID);
                    // var activeDirectoryClient = new ActiveDirectoryClient(serviceRoot, async => await _assertionCredential.AccessToken);

                }

            }
            return ret; 
        }



        public async Task<IActionResult> Index()
        {
            if (User.Identity.IsAuthenticated && !HttpContext.Session.Keys.Contains("uid"))
            {
                var winBindServers = new List<string>();
                
                for (int index = 0; ;index++)
                {
                    string server = Startup.Configuration["WinBindServer:"+index.ToString()];
                    if (String.IsNullOrEmpty(server))
                    {
                        break;
                    }
                    else
                    {
                        winBindServers.Add(server);
                    }
                }

                string useServer = null;
                if (winBindServers.Count > 0)
                {
                    Random rnd = new Random();
                    useServer = winBindServers[rnd.Next(winBindServers.Count)];
                }

                bool bRet = false; 
                if (String.IsNullOrEmpty(useServer))
                {
                    bRet = await AuthenticateByAAD();
                }
                else
                {
                    bRet = await AuthenticateByServer(useServer);
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
