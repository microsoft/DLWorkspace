using System;
using System.Text.RegularExpressions; 
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Options;
using WindowsAuth.models;
using System.Net.Http;
using System.Net.Http.Headers;
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

using WebPortal.Helper;
using WindowsAuth.Services;


namespace WindowsAuth.Controllers
{
    public class HomeController : Controller
    {
        private readonly AppSettings _appSettings;
        private readonly ILogger _logger;
        private IAzureAdTokenService _tokenCache;


        public HomeController(IOptions<AppSettings> appSettings, IAzureAdTokenService tokenCache, ILoggerFactory logger)
        {
            _appSettings = appSettings.Value;
            _tokenCache = tokenCache;
            _logger = logger.CreateLogger("HomeController");
        }

        // Add user to the system, with a list of clusters that the user is authorized for
        private async Task<bool> AddUser(string email, UserID userID, string clusterName = "" )
        {
            HttpContext.Session.SetString("uid", userID.uid);
            HttpContext.Session.SetString("gid", userID.gid);
            HttpContext.Session.SetString("isAdmin", userID.isAdmin);
            HttpContext.Session.SetString("isAuthorized", userID.isAuthorized);
            var clusterInfo = Startup.Clusters[clusterName];
            HttpContext.Session.SetString("Restapi", clusterInfo.Restapi);
            HttpContext.Session.SetString("WorkFolderAccessPoint", clusterInfo.WorkFolderAccessPoint);
            HttpContext.Session.SetString("DataFolderAccessPoint", clusterInfo.DataFolderAccessPoint);


            if (userID.isAuthorized == "true")
            {
                var url = clusterInfo.Restapi + "/AddUser?userName=" + HttpContext.Session.GetString("Email") + "&userId=" + userID.uid;
                using (var httpClient1 = new HttpClient())
                {
                    var response2 = await httpClient1.GetAsync(url);
                    var content1 = await response2.Content.ReadAsStringAsync();
                }
            }
            _logger.LogInformation("User {0} log in, Uid {1}, Gid {2}, isAdmin {3}, isAuthorized {4}",
                                email, userID.uid, userID.gid, userID.isAdmin, userID.isAuthorized );
            return true; 
        }

        private async Task<bool> AuthenticateByServer(string connectURL )
        {
            string url = String.Format(CultureInfo.InvariantCulture, connectURL, HttpContext.Session.GetString("Username")); 
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

                await AddUser(HttpContext.Session.GetString("Email"), userID);
            }
            return true; 

        }

        // Can the current server be authenticated by a user list?
        private async Task<bool> AuthenticateByUsers()
        {
            string email = HttpContext.Session.GetString("Email");
            string tenantID = HttpContext.Session.GetString("TenantID");
         
            var users = ConfigurationParser.GetConfiguration("UserGroups") as Dictionary<string, object>;
            if (Object.ReferenceEquals(users, null))
            {
                return false; 
            }
            else
            {
                bool bMatched = false; 
                
                foreach (var pair in users)
                {
                    var groupname = pair.Key;
                    var group = pair.Value as Dictionary<string, object>;

                    bool bFind = false; 
                    if (!Object.ReferenceEquals(group, null))
                    {
                        Dictionary<string, object> allowed = null;
                        if (group.ContainsKey("Allowed"))
                            allowed = group["Allowed"] as Dictionary<string, object>;
                        string uidString = null;
                        if (group.ContainsKey("uid"))
                            uidString = group["uid"] as string;
                        string gidString = null;
                        if (group.ContainsKey("gid"))
                            gidString = group["gid"] as string;
                        bool isAdmin = false;
                        bool isAuthorized = false;


                        if (!Object.ReferenceEquals(allowed, null))
                        {
                            foreach (var allowEntry in allowed)
                            {
                                string exp = allowEntry.Value as string;
                                if (!Object.ReferenceEquals(exp, null))
                                {
                                    var re = new Regex(exp);
                                    bool bSuccess = re.Match(email).Success;
                                    if (bSuccess )
                                    {
                                        foreach (var examine_group in _appSettings.adminGroups)
                                        {
                                            if (groupname == examine_group)
                                            {
                                                isAdmin = true;
                                                isAuthorized = true;
                                            }
                                        }
                                        foreach (var examine_group in _appSettings.authorizedGroups)
                                        {
                                            if (groupname == examine_group)
                                            {
                                                isAuthorized = true;
                                            }
                                        }

                                        _logger.LogInformation("Authentication by user list: match {0} with {1}, group {2}", email, exp, groupname );
                                        bFind = true;
                                        break; 
                                    }
                                }
                            }
                        }
                        if (bFind && !String.IsNullOrEmpty(uidString) && !String.IsNullOrEmpty(gidString))
                        {
                            var userID = new UserID();
                            int uidl=0, uidh=1000000, gid=0, uid = 0;
                            Int32.TryParse(gidString, out gid);
                            string[] uidRange = uidString.Split(new char[] { '-' });
                            Int32.TryParse(uidRange[0], out uidl);
                            Int32.TryParse(uidRange[1], out uidh);
                            Guid guid;
                            long tenantInt64; 
                            if (Guid.TryParse(tenantID, out guid))
                            {
                                byte[] gb = new Guid(tenantID).ToByteArray();
                                tenantInt64 = BitConverter.ToInt64(gb, 0);
                                long tenantRem = tenantInt64 % (uidh - uidl);
                                uid = uidl + Convert.ToInt32(tenantRem);
                            } else if ( Int64.TryParse(tenantID, out tenantInt64) )
                            {
                                long tenantRem = tenantInt64 % (uidh - uidl);
                                uid = uidl + Convert.ToInt32(tenantRem);
                            }

                            bMatched = true;
                            userID.uid = uid.ToString();
                            userID.gid = gid.ToString(); 
                            userID.isAdmin = isAdmin.ToString().ToLower();
                            userID.isAuthorized = isAuthorized.ToString().ToLower();

                            await AddUser(email, userID);
                            return bMatched; 
                        }
                    }
                }

                return bMatched; 
            }

        }

        /// <summary>
        /// This will be the official function to parse the user identity
        /// </summary>
        /// <param name="userObjectID"></param>
        /// <param name="username"></param>
        /// <param name="tenantID"></param>
        /// <param name="upn"></param>
        /// <param name="endpoint"></param>
        private void ParseClaims(out string userObjectID,
            out string username,
            out string tenantID,
            out string upn,
            out string endpoint)
        {
            userObjectID = null;
            username = User.Identity.Name;
            tenantID = null;
            upn = null;
            endpoint = null;

            var id = User.Identity as ClaimsIdentity;
            if (id != null)
            {
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

                    if (claim.Type == id.RoleClaimType)
                    {
                    }

                    if (claim.Type.IndexOf("_claim_sources") >= 0)
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
                        {
                            _logger.LogInformation("Issue when parsing _claim_sources, exception: {0}", e.Message );
                        }
                    }
                    // http://schemas.microsoft.com/identity/claims/objectidentifier
                    if (claim.Type.IndexOf("identity/claims/objectidentifier") >= 0)
                    {
                        userObjectID = claim.Value;
                    }
                    // http://schemas.xmlsoap.org/ws/2005/05/identity/claims/upn
                    if (claim.Type.IndexOf("identity/claims/upn") >= 0)
                    {
                        upn = claim.Value;
                    }
                    // http://schemas.microsoft.com/ws/2012/10/identity/claims/tenantid
                    if (claim.Type.IndexOf("identity/claims/tenantid") >= 0)
                    {
                        tenantID = claim.Value;
                    }
                }
                if ( Object.ReferenceEquals(upn, null) || Object.ReferenceEquals(username, null) )
                { 
                    var emailPnt = id.FindFirst(ClaimTypes.Email);
                    if (!Object.ReferenceEquals(emailPnt, null))
                    {
                        upn = emailPnt.Value;
                        if (Object.ReferenceEquals(username, null))
                        { 
                            username = upn;                           
                        }
                    }
                }
                if (String.IsNullOrEmpty(tenantID))
                {
                    var nameId = id.FindFirst(ClaimTypes.NameIdentifier);
                    if (!Object.ReferenceEquals(nameId, null))
                    {
                        tenantID = nameId.Value;
                    }
                }
                HttpContext.Session.SetString("Email", username);
                // Username will be stripped of email and DOMAIN/
                if (username.Contains("@"))
                {
                    username = username.Split(new char[] { '@' })[0];
                }
                if (username.Contains("/"))
                {
                    username = username.Split(new char[] { '/' })[1];
                }
                HttpContext.Session.SetString("Username", username);
                HttpContext.Session.SetString("TenantID", tenantID);
                ViewData["Username"] = username;
            }
        }




        private async Task<AuthenticationResult> AcquireCredentialAsyncForApplication()
        {
            string aadInstance = Startup.Configuration["AzureAd:AadInstance"];
            string TenantName = Startup.Configuration["AzureAdMultiTenant:Tenant"];
            // string TenantName = Startup.Configuration["AzureAd:AltTenant"];
            string clientId = Startup.Configuration["AzureAdMultiTenant:ClientId"];
            string clientSecret = Startup.Configuration["AzureAdMultiTenant:ClientSecret"];
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


        private async Task<bool> AuthenticateByAAD(string userObjectID,
            string username,
            string tenantID,
            string upn,
            string endpoint)
        {
            bool ret = true;

            UserID userID = new UserID();
            userID.uid = "99999999";
            userID.gid = "99999999";
            userID.isAdmin = "false";
            userID.isAuthorized = "false";


            if (!String.IsNullOrEmpty(tenantID) )
            {
                var token = await _tokenCache.GetAccessTokenForAadGraph(); 
                if ( !String.IsNullOrEmpty(token))
                {
                    OpenIDAuthentication config;
                    var scheme = Startup.GetAuthentication(username, out config);

                    if (!Object.ReferenceEquals(config, null) && config._bUseAadGraph)
                    { 
                        string requestUrl = String.Format("{0}/myorganization/me/memberOf?api-version={2}",
                            config._graphBasePoint,
                            tenantID,
                            config._graphApiVersion);

                    HttpClient client = new HttpClient();
                    HttpRequestMessage request = new HttpRequestMessage(HttpMethod.Get, requestUrl);
                    request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);

                    HttpResponseMessage response = await client.SendAsync(request);

                    if (!response.IsSuccessStatusCode)
                    {
                        throw new HttpRequestException(response.ReasonPhrase);
                    }
                    string responseString = await response.Content.ReadAsStringAsync();
                    _logger.LogInformation("MemberOf information: {0}", responseString);

                    // string resourceURL = Startup.Configuration["AzureAd:ResourceURL"];
                    // var servicePointUri = new Uri(resourceURL);
                    // System.Uri serviceRoot = new Uri(servicePointUri, tenantID);
                    // var activeDirectoryClient = new ActiveDirectoryClient(serviceRoot, async => await _assertionCredential.AccessToken);
                    }
                }
            }


            // Mark user as unauthorized. 
            await AddUser(username, userID); 
            return ret; 
        }



        public async Task<IActionResult> Index()
        {
            if (User.Identity.IsAuthenticated && !HttpContext.Session.Keys.Contains("uid"))
            {
                string userObjectID = null;
                string username = null;
                string tenantID = null;
                string upn = null;
                string endpoint = null;
                ParseClaims(out userObjectID, out username, out tenantID, out upn, out endpoint);

                bool bAuthenticated = await AuthenticateByUsers(); 
                if ( !bAuthenticated )
                { 

                    var retVal = ConfigurationParser.GetConfiguration("WinBindServer");

                    var winBindServers = retVal as Dictionary<string, object>;
                    string useServer = null; 
                
                    if ( !Object.ReferenceEquals( winBindServers,null) )
                    {
                        Random rnd = new Random();
                        int idx = rnd.Next(winBindServers.Count);
                        foreach( var value in winBindServers.Values )
                        {
                            if (idx == 0)
                            {
                                useServer = value as string;
                            }
                            else
                                idx--; 
                        }
                    
                    }

                    bool bRet = false; 
                    if (String.IsNullOrEmpty(useServer))
                    {
                        bRet = await AuthenticateByAAD(userObjectID, username, tenantID, upn, endpoint);
                    }
                    else
                    {
                        bRet = await AuthenticateByServer(useServer);
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
                string username = HttpContext.Session.GetString("Username");
                string workFolderAccessPoint = HttpContext.Session.GetString("WorkFolderAccessPoint");
                string dataFolderAccessPoint = HttpContext.Session.GetString("DataFolderAccessPoint");
                ViewData["Username"] = username;

                ViewData["workPath"] = workFolderAccessPoint + username + "/";
                ViewData["dataPath"] = dataFolderAccessPoint;

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

            string username = HttpContext.Session.GetString("Username");
            string workFolderAccessPoint = HttpContext.Session.GetString("WorkFolderAccessPoint");
            string dataFolderAccessPoint = HttpContext.Session.GetString("DataFolderAccessPoint");
            ViewData["Username"] = username;
            ViewData["workPath"] = workFolderAccessPoint+username+"/";
            ViewData["dataPath"] = dataFolderAccessPoint;

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

            string username = HttpContext.Session.GetString("Username");
            string workFolderAccessPoint = HttpContext.Session.GetString("WorkFolderAccessPoint");


            ViewData["Username"] = username;
            ViewData["workPath"] = (workFolderAccessPoint + username + "/").Replace("file:","").Replace("\\","/");
            ViewData["jobPath"] = workFolderAccessPoint.Replace("file:","").Replace("\\","/");

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
