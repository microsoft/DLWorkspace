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
using System.Threading;
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
using Microsoft.AspNetCore.Mvc.Rendering;

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

        private string ParseToUsername(string email)
        {
            string username = email;
            if (username.Contains("@"))
            {
                username = username.Split('@')[0];
            }
            if (username.Contains("/"))
            {
                username = username.Split('/')[1];
            }
            return username;
        }

        private void UserUnauthorized()
        {
            HttpContext.Session.SetString("uid", "9999999");
            HttpContext.Session.SetString("gid", "9999999");
            HttpContext.Session.SetString("isAdmin", "false");
            HttpContext.Session.SetString("isAuthorized", "false");
            HttpContext.Session.SetString("Restapi", "");
            HttpContext.Session.SetString("WorkFolderAccessPoint", "");
            HttpContext.Session.SetString("DataFolderAccessPoint", "");

        }

        // Add user to the system, with a list of clusters that the user is authorized for
        private async Task<bool> AddUser(UserEntry userEntry, string clusterName)
        {
            var email = userEntry.Alias;
            HttpContext.Session.SetString("Email", userEntry.Alias);
            var username = ParseToUsername(userEntry.Alias);
            HttpContext.Session.SetString("Username", username);
            HttpContext.Session.SetString("uid", userEntry.uid);
            HttpContext.Session.SetString("gid", userEntry.gid);
            HttpContext.Session.SetString("isAdmin", userEntry.isAdmin);
            HttpContext.Session.SetString("isAuthorized", userEntry.isAuthorized);
            var clusterInfo = Startup.Clusters[clusterName];
            HttpContext.Session.SetString("Restapi", clusterInfo.Restapi);
            HttpContext.Session.SetString("WorkFolderAccessPoint", clusterInfo.WorkFolderAccessPoint);
            HttpContext.Session.SetString("DataFolderAccessPoint", clusterInfo.DataFolderAccessPoint);
            HttpContext.Session.SetString("smbUsername", clusterInfo.smbUsername);
            HttpContext.Session.SetString("smbUserPassword", clusterInfo.smbUserPassword);


            if (userEntry.isAuthorized == "true")
            {
                var url = clusterInfo.Restapi + "/AddUser?userName=" + HttpContext.Session.GetString("Email") + "&userId=" + userEntry.uid;
                using (var httpClient1 = new HttpClient())
                {
                    var response2 = await httpClient1.GetAsync(url);
                    var content1 = await response2.Content.ReadAsStringAsync();
                }
            }
            _logger.LogInformation("User {0} log in, Uid {1}, Gid {2}, isAdmin {3}, isAuthorized {4}",
                               email, userEntry.uid, userEntry.gid, userEntry.isAdmin, userEntry.isAuthorized);
            return true;
        }
        
        private async Task<UserID> FindGroupMembershipByServer(string connectURL)
        {
            string url = String.Format(CultureInfo.InvariantCulture, connectURL, HttpContext.Session.GetString("Email"));
            UserID userID = null;
            try
            {
                using (var httpClient = new HttpClient())
                {
                    var response1 = await httpClient.GetAsync(url);
                    var content = await response1.Content.ReadAsStringAsync();
                    userID = JsonConvert.DeserializeObject<UserID>(content.Trim()) as UserID;
                    userID.isAdmin = "false";
                    userID.isAuthorized = "false";
                }
                return userID;
            }
            catch
            {
                return null;
            }
        }

        private Dictionary<string, UserID> AuthenticateUserByGroupMembership(List<UserID> lst)
        {
            var authorizedClusters = new Dictionary<string, UserID>(StringComparer.OrdinalIgnoreCase);

            if (lst.Count() == 0)
                return authorizedClusters;
            var clusters = Startup.Clusters;
            foreach (var pair in clusters)
            {
                var clusterName = pair.Key;
                var clusterInfo = pair.Value;
                foreach (var userID in lst)
                {
                    foreach (var group in userID.groups)
                    {
                        if (clusterInfo.AdminGroups.ContainsKey(group))
                        {
                            userID.isAdmin = "true";
                            userID.isAuthorized = "true";
                            authorizedClusters[clusterName] = userID;
                        }
                    }
                }
                // Check for authorization
                if (!authorizedClusters.ContainsKey(clusterName))
                {
                    foreach (var userID in lst)
                    {
                        foreach (var group in userID.groups)
                        {
                            if (clusterInfo.AuthorizedGroups.ContainsKey(group))
                            {
                                userID.isAdmin = "false";
                                userID.isAuthorized = "true";
                                authorizedClusters[clusterName] = userID;
                            }
                        }
                    }
                }
                // Check for registration 
                if (!authorizedClusters.ContainsKey(clusterName))
                {
                    foreach (var userID in lst)
                    {
                        foreach (var group in userID.groups)
                        {
                            if (clusterInfo.RegisterGroups.ContainsKey(group))
                            {
                                //userID.uid = "-1";
                                userID.isAdmin = "false";
                                userID.isAuthorized = "false";
                                authorizedClusters[clusterName] = userID;
                            }
                        }
                    }
                }

            }
            return authorizedClusters;
        }

        // Can the current user be recognized for its uid/gid through an explicit listed usergroups?
        // Return a list of UserID (and matching groups) that the current user belongs to
        private List<UserID> FindGroupMembershipByUserGroups()
        {
            string email = HttpContext.Session.GetString("Email");
            string tenantID = HttpContext.Session.GetString("TenantID");

            // Find Groups that the user belong to
            var ret = new List<UserID>();
            var users = ConfigurationParser.GetConfiguration("UserGroups") as Dictionary<string, object>;
            if (Object.ReferenceEquals(users, null))
            {
                return ret;
            }
            else
            {
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

                        if (!Object.ReferenceEquals(allowed, null) && !String.IsNullOrEmpty(uidString) && !String.IsNullOrEmpty(gidString))
                        {
                            foreach (var allowEntry in allowed)
                            {
                                string exp = allowEntry.Value as string;
                                if (!Object.ReferenceEquals(exp, null))
                                {
                                    var re = new Regex(exp);
                                    bool bSuccess = re.Match(email).Success;
                                    if (bSuccess)
                                    {
                                        _logger.LogInformation("Authentication by user list: match {0} with {1}, group {2}", email, exp, groupname);
                                        bFind = true;
                                        break;
                                    }
                                }
                            }
                        }
                        if (bFind)
                        {
                            var userID = new UserID();

                            long uidl = 0, uidh = 1000000, gid = 0, uid = -1;
                            Int64.TryParse(gidString, out gid);  
                            string[] uidRange = uidString.Split(new char[] { '-' });
                            Int64.TryParse(uidRange[0], out uidl);
                            if ( uidRange.Length > 1 )
                            { 
                                Int64.TryParse(uidRange[1], out uidh);
                            }
                            else
                            {
                                uidh = uidl; 
                            }
                            Guid guid;
                            Int64 tenantInt64;
                            if (Guid.TryParse(tenantID, out guid))
                            {
                                byte[] gb = new Guid(tenantID).ToByteArray();
                                tenantInt64 = BitConverter.ToInt64(gb, 0);
                                if ( uidh > uidl )
                                { 
                                    long tenantRem = tenantInt64 % (uidh - uidl);
                                    uid = uidl + Convert.ToInt32(tenantRem);
                                }
                                else
                                {
                                    uid = uidl; 
                                }
                            } else if (Int64.TryParse(tenantID.Substring(18), out tenantInt64))
                            {
                                if ( uidh > uidl )
                                { 
                                    long tenantRem = tenantInt64 % (uidh - uidl);
                                    uid = uidl + Convert.ToInt32(tenantRem);
                                }
                                else
                                {
                                    uid = uidl; 
                                }
                            }
                            userID.uid = uid.ToString();
                            userID.gid = gid.ToString();
                            userID.groups = new List<string>();
                            userID.groups.Add(groupname);
                            ret.Add(userID);

                        }
                    }
                }
                return ret;
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
                            _logger.LogInformation("Issue when parsing _claim_sources, exception: {0}", e.Message);
                        }
                    }
                    // http://schemas.microsoft.com/identity/claims/objectidentifier
                    if (claim.Type.IndexOf("identity/claims/objectidentifier") >= 0)
                    {
                        userObjectID = claim.Value;
                    }
                    if (claim.Type.IndexOf("identity/claims/nameidentifier")>=0)
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
                if (Object.ReferenceEquals(upn, null) || Object.ReferenceEquals(username, null))
                {
                    var emailPnt = id.FindFirst(ClaimTypes.Email);
                    if (!Object.ReferenceEquals(emailPnt, null))
                    {
                        upn = emailPnt.Value;
                        username = upn;
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
                username = ParseToUsername(username);
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

        private async Task<UserEntry> AuthenticateByOneDB(string email, string tenantID, ClusterContext db, UserID userID)
        {
            var priorEntrys = db.User.Where(b => b.Email == email).ToAsyncEnumerable();

            long nEntry = 0;
            UserEntry ret = null;
            // Prior entry exists? 
            await priorEntrys.ForEachAsync(entry =>
           {
               // We will not update existing entry in database. 
               // db.Entry(entry).CurrentValues.SetValues(userEntry);
               ret = entry;
               Interlocked.Add(ref nEntry, 1);
           }
            );
            if (Interlocked.Read(ref nEntry) == 0)
            {
                if (!Object.ReferenceEquals(userID, null))
                {
                    string password = Guid.NewGuid().ToString().Substring(0, 8);
                    UserEntry userEntry = new UserEntry(userID, email, email, password);
                    await db.User.AddAsync(userEntry);
                    await db.SaveChangesAsync();
                    return userEntry;
                }
                else
                    return null;
            }
            else
            {
                // Prior entry exists, we use the database as the authorative source. 
                UserEntry newEntry = ret;
                // Update is AuthorizedEntry only, other entry will be updated by database. 
                if (!Object.ReferenceEquals(userID, null))
                {
                    bool bUpdate = false;

                    if (String.Compare(ret.isAuthorized, userID.isAuthorized, true) < 0 || String.Compare(ret.isAdmin, userID.isAdmin, true) < 0)
                    {
                        // userID isAuthorized is true
                        newEntry.isAuthorized = userID.isAuthorized;
                        newEntry.isAdmin = userID.isAdmin;
                        newEntry.uid = userID.uid;
                        newEntry.gid = userID.gid;

                        bUpdate = true;
                    }

                    if (bUpdate)
                    {
                        db.Entry(ret).CurrentValues.SetValues(newEntry);
                        await db.SaveChangesAsync();
                    }
                }
                if (newEntry.Alias != newEntry.Email)
                {
                    return await AuthenticateByOneDB(newEntry.Alias, tenantID, db, userID);
                }
                else
                    return newEntry;
            }
        }

        private async Task<bool> AuthenticateByDB(string email,
            string tenantID,
            string username,
            Dictionary<string, UserID> authorizationIn,
            Dictionary<string, UserEntry> authorizationOut)
        {
            var databases = Startup.Database;
            var tasks = new List<Task<UserEntry>>();
            var lst = new List<string>();

            foreach (var pair in databases)
            {
                var clusterName = pair.Key;
                var db = pair.Value;
                var userID = authorizationIn.ContainsKey(clusterName) ? authorizationIn[clusterName] : null;

                tasks.Add(AuthenticateByOneDB(email, tenantID, db, userID));
                lst.Add(clusterName);
            }
            await Task.WhenAll(tasks);
            for (int i = 0; i < lst.Count(); i++)
            {
                var userEntry = tasks[i].Result;
                if (!Object.ReferenceEquals(userEntry, null))
                {
                    authorizationOut[lst[i]] = userEntry;
                }
            }

            // Remove all clusters that the user is not authorized. 
            lst.Clear();
            foreach (var pair in authorizationOut)
            {
                UserEntry userID = pair.Value;
                if (userID.isAdmin.ToLower() == "true")
                {
                    userID.isAdmin = "true";
                    userID.isAuthorized = "true";
                }
                else if (userID.isAuthorized.ToLower() == "true")
                {
                    userID.isAuthorized = "true";
                }
                else
                    lst.Add(pair.Key);
            }
            foreach (var clusterName in lst)
            {
                authorizationOut.Remove(clusterName);
            }
            return true;
        }

        private async Task<bool> AuthenticateByAAD(string userObjectID,
            string username,
            string tenantID,
            string upn,
            string endpoint)
        {
            bool ret = true;

            UserID userID = new UserID();
            userID.groups = new List<string>();
            userID.uid = "99999999";
            userID.gid = "99999999";
            userID.isAdmin = "false";
            userID.isAuthorized = "false";


            if (!String.IsNullOrEmpty(tenantID))
            {
                var token = await _tokenCache.GetAccessTokenForAadGraph();
                if (!String.IsNullOrEmpty(token))
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
            // await AddUser(username, userID); 
            return ret;
        }

        /*
        public async Task<int> UpdateUser(string email, UserID userID, string clusterName )
        {
            var userEntry = new UserEntry(userID, email);
            var db = Startup.DatabaseForUser[clusterName];
            var priorEntrys = db.User.Where(b => b.Email == email).ToAsyncEnumerable();
            long  nEntry = 0; 
            await priorEntrys.ForEachAsync( entry =>
                { 
                    // We will not update existing entry in database. 
                    // db.Entry(entry).CurrentValues.SetValues(userEntry);
                    Interlocked.Add(ref nEntry, 1);
                }
            );
            if (Interlocked.Read(ref nEntry) == 0)
            {
                await db.User.AddAsync(userEntry);
            }
            return await db.SaveChangesAsync();
        }

        public async Task<int> UpdateUserToAll(string email, UserID userID)
        {
            await Task.WhenAll(Startup.DatabaseForUser.Select(pair => UpdateUser(email, userID, pair.Key)));
            return 0;
        }*/

#region ASP Controllers
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

                var retVal = ConfigurationParser.GetConfiguration("WinBindServers");

                var winBindServers = retVal as Dictionary<string, object>;

                var lst = ((Object.ReferenceEquals(winBindServers, null) || winBindServers.Count() == 0) ? FindGroupMembershipByUserGroups() : new List<UserID>());

                if (true)
                {
                    var email = HttpContext.Session.GetString("Email");
                    string useServer = null;

                    if (!Object.ReferenceEquals(winBindServers, null))
                    {
                        Random rnd = new Random();
                        int idx = rnd.Next(winBindServers.Count);
                        foreach (var value in winBindServers.Values)
                        {
                            if (idx == 0)
                            {
                                useServer = value as string;
                            }
                            else
                                idx--;
                        }
                    }

                    if (!String.IsNullOrEmpty(useServer))
                    {
                        _logger.LogDebug($"Attempt to contact WinBind server {useServer} for membershhip");
                        var userID = await FindGroupMembershipByServer(useServer);
                        if (!Object.ReferenceEquals(userID, null))
                            lst.Add(userID);
                    }
                    _logger.LogDebug("User {0} group memberships {1}", email, string.Join(",", lst.SelectMany(x => x.groups).ToArray()));

                    var authorizedClusters = AuthenticateUserByGroupMembership(lst);
                    _logger.LogDebug("User {0} authorized clusters preDB {1}", email, string.Join(",", authorizedClusters.Keys.ToArray()));
                    var authorizationFinal = new Dictionary<string, UserEntry>();
                    var ret = await AuthenticateByDB(upn, tenantID, username, authorizedClusters, authorizationFinal);
                    _logger.LogDebug("User {0} authorized clusters afterDB {1}", email, string.Join(",", authorizationFinal.Keys.ToArray()));

                    // bRet = await AuthenticateByAAD(userObjectID, username, tenantID, upn, endpoint);
                    string useCluster = "";

                    if (authorizationFinal.Count() > 0)
                    {
                        foreach (var pair in authorizationFinal)
                        {

                            await AddUser(pair.Value, pair.Key);
                            useCluster = pair.Key;
                            _logger.LogInformation("User {0} is authorized for cluster {1}", email, pair.Key);
                        }
                    }
                    // Store authorized clusters.
                    HttpContext.Session.SetString("AuthorizedClusters", JsonConvert.SerializeObject(authorizationFinal));
                    HttpContext.Session.SetString("CurrentClusters", useCluster);
                    var lstClusters = authorizedClusters.Keys.ToList<string>();
                    HttpContext.Session.SetString("ClustersList", JsonConvert.SerializeObject(lstClusters));
                    if (String.IsNullOrEmpty(useCluster))
                    {
                        // Mark user as unauthorized.
                        UserUnauthorized();
                        _logger.LogInformation("User {0} is not authorized for any cluster ... ", email);
                    }
                }
            }


            var vm = new ClusterSelectViewModel();

            if (HttpContext.Session.Keys.Contains("isAuthorized"))
            {
                if (HttpContext.Session.GetString("isAuthorized") == "true")
                {
                    ViewData["isAuthorized"] = true;
                    _logger.LogInformation("Try to render SelectCluster");
                    var info = HttpContext.Session.GetString("CurrentClusters");
                    ViewData["CurrentCluster"] = info;
                    vm.CurrentCluster = info;
                    var lstClustersInfo = HttpContext.Session.GetString("ClustersList");
                    var lstClusters = (String.IsNullOrEmpty(info) ? new List<string>() : JsonConvert.DeserializeObject<List<string>>(lstClustersInfo));
                    vm.ClustersList = new List<SelectListItem>();
                    for (int i = 0; i < lstClusters.Count(); i++)
                    {
                        if ( !String.IsNullOrEmpty(lstClusters[i]))
                        {
                            vm.ClustersList.Add(new SelectListItem
                            {
                                Value = lstClusters[i], // (i + 1).ToString(),
                                Text = lstClusters[i]
                            });
                            _logger.LogInformation("Cluster Option {0} is {1}", i + 1, lstClusters[i]);
                        }
                    };
                    _logger.LogInformation("Authentication information examined...");
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
                string smbUsername = HttpContext.Session.GetString("smbUsername");
                string smbUserPassword = HttpContext.Session.GetString("smbUserPassword");
                ViewData["Username"] = username;

                ViewData["workPath"] = workFolderAccessPoint + username + "/";
                ViewData["dataPath"] = dataFolderAccessPoint;
                ViewData["smbUsername"] = smbUsername;
                ViewData["smbUserPassword"] = smbUserPassword;
                var configString = Startup.DashboardConfig.ToString();
                var configArray = ASCIIEncoding.ASCII.GetBytes(configString);
                ViewData["Dashboard"] = Convert.ToBase64String(configArray) ;
                _logger.LogInformation("Dash board prepared ...");
            }
            return View(vm);
        }

        public IActionResult SelectCluster()
        {
            var vm = new ClusterSelectViewModel();
            _logger.LogInformation("Try to render SelectCluster");
            var info = HttpContext.Session.GetString("CurrentClusters");
            vm.CurrentCluster = HttpContext.Session.GetString("ClustersList");
            var lstClusters = (String.IsNullOrEmpty(info) ? new List<string>() : JsonConvert.DeserializeObject<List<string>>(info));
            vm.ClustersList = new List<SelectListItem>();
            for (int i = 0; i < lstClusters.Count(); i++)
            {
                vm.ClustersList.Add(new SelectListItem
                {
                    Value = (i + 1).ToString(),
                    Text = lstClusters[i]
                });
                _logger.LogInformation("Cluster Option {0} is {1}", i + 1, lstClusters[i]);
            };
            return View(vm);
        }

        [HttpPost]
        [ValidateAntiForgeryToken]
        public async Task<IActionResult> SelectCluster(ClusterSelectViewModel model )
        {
            if ( ModelState.IsValid)
            {
                var clusterInfo = HttpContext.Session.GetString("AuthorizedClusters");
                var authorizedClusters = JsonConvert.DeserializeObject<Dictionary<string, UserEntry>>(clusterInfo);
                var useCluster = model.CurrentCluster;
                if (authorizedClusters.ContainsKey(useCluster))
                {
                    HttpContext.Session.SetString("CurrentClusters", useCluster);
                    await AddUser(authorizedClusters[useCluster], useCluster);
                }
            }
            return RedirectToAction("Index", "Home");
        }

        public IActionResult JobSubmission()
        {
            if (!User.Identity.IsAuthenticated)
            {
                return RedirectToAction("Index", "Home");
            }

            if (!HttpContext.Session.Keys.Contains("isAuthorized") || HttpContext.Session.GetString("isAuthorized") != "true")
            {
                return RedirectToAction("Index", "Home");
            }

            string workFolderAccessPoint = HttpContext.Session.GetString("WorkFolderAccessPoint");
            string dataFolderAccessPoint = HttpContext.Session.GetString("DataFolderAccessPoint");

            ViewData["workPath"] = workFolderAccessPoint + HttpContext.Session.GetString("Username") + "/";
            ViewData["dataPath"] = dataFolderAccessPoint;

            ViewData["uid"] = HttpContext.Session.GetString("uid");
            ViewData["gid"] = HttpContext.Session.GetString("gid");

            ViewData["username"] = HttpContext.Session.GetString("Username");

            ViewData["mode"] = (HttpContext.Request.Query.ContainsKey("Mode") && HttpContext.Request.Query["Mode"] == "templates") ? "Templates" : "JobSubmission";

            ViewData["isAdmin"] = HttpContext.Session.GetString("isAdmin");
            ViewData["cluster"] =  HttpContext.Session.GetString("CurrentClusters");
            AddViewData(message: "Your application description page.");
            return View();
        }

        public IActionResult ViewJobs()
        {
            if (!User.Identity.IsAuthenticated)
            {
                return RedirectToAction("Index", "Home");
            }

            if (!HttpContext.Session.Keys.Contains("isAuthorized") || HttpContext.Session.GetString("isAuthorized") != "true")
            {
                return RedirectToAction("Index", "Home");
            }


            ViewData["isAdmin"] = HttpContext.Session.GetString("isAdmin");

            AddViewData(message: "View and Manage Your Jobs.");
            return View();
        }

        public IActionResult JobDetail()
        {
            if (!User.Identity.IsAuthenticated)
            {
                return RedirectToAction("Index", "Home");
            }
            if (!HttpContext.Session.Keys.Contains("isAuthorized") || HttpContext.Session.GetString("isAuthorized") != "true")
            {
                return RedirectToAction("Index", "Home");
            }
            ViewData["jobid"] = HttpContext.Request.Query["jobId"];
            string workFolderAccessPoint = HttpContext.Session.GetString("WorkFolderAccessPoint");


            ViewData["workPath"] = (workFolderAccessPoint + HttpContext.Session.GetString("Username") + "/").Replace("file:", "").Replace("\\", "/");
            ViewData["jobPath"] = workFolderAccessPoint.Replace("file:", "").Replace("\\", "/");
            AddViewData(message: "View and Manage Your Jobs.");
            return View();
        }

        public IActionResult ViewCluster()
        {
            if (!User.Identity.IsAuthenticated)
            {
                // return RedirectToAction("Login", "Account", new { controller = "Account", action = "Login" });
                return RedirectToAction("Index", "Home");
            }
            if (!HttpContext.Session.Keys.Contains("isAuthorized") || HttpContext.Session.GetString("isAuthorized") != "true")
            {
                return RedirectToAction("Index", "Home");
            }

            AddViewData(message: "Cluster Status.");

            return View();
        }

        public IActionResult About()
        {
            AddViewData(message: "Your application description page.");
            return View();
        }

        public IActionResult Contact()
        {
            AddViewData(message: "Your contact page.");
            return View();
        }

        public IActionResult Error()
        {
            AddViewData();
            return View();
        }

        public void AddViewData(string message = "")
        {
            string username = HttpContext.Session.GetString("Username");
            ViewData["Username"] = username;

            if (message != "")
                ViewData["Message"] = message;
        }

        public async Task<IActionResult> ManageUser()
        {
            AddViewData();
            var currentCluster = HttpContext.Session.GetString("CurrentClusters");
            if (Startup.Database.ContainsKey(currentCluster))
            {
                if (!User.Identity.IsAuthenticated || HttpContext.Session.GetString("isAdmin").Equals("false") )
                {
                    return RedirectToAction("Index", "Home");
                }
                var db = Startup.Database[currentCluster];
                if (!Object.ReferenceEquals(db, null))
                {
                    if (HttpContext.Request.Query.ContainsKey("AccountChangeEmail"))
                    {
                        string email = HttpContext.Request.Query["AccountChangeEmail"];
                        UserEntry userEntry = db.User.First(x => x.Email.Equals(email));
                       // db.User.Update(userEntry);
                        if (userEntry.isAdmin.Equals("true"))
                        {
                            userEntry.isAdmin = "false";
                            userEntry.isAuthorized = "false";
                        }
                        else if (userEntry.isAuthorized.Equals("false"))
                        {
                            userEntry.isAuthorized = "true";
                        }
                        else
                        {
                            userEntry.isAdmin = "true";
                        }
                        await db.SaveChangesAsync();
                    }                  
                    List<string[]> userTable = new List<string[]>();
                    foreach (var user in db.User)
                    {
                        string accountType = (user.Email == user.Alias) ? GetAccountType(user.isAuthorized == "true", user.isAdmin == "true") : "Alias";
                        string[] userString = new string[] { ParseToUsername(user.Alias), user.Email, accountType };
                        userTable.Add(userString);
                    }
                    ViewData["Users"] = userTable;
                }
            }
            return View();
        }

        public async Task<IActionResult> AccountSettings()
        {
            if (!User.Identity.IsAuthenticated)
            {
                return RedirectToAction("Index", "Home");
            }

            string userEmail = HttpContext.Session.GetString("Email");

            var currentCluster = HttpContext.Session.GetString("CurrentClusters");
            if (Startup.Database.ContainsKey(currentCluster))
            {
                var db = Startup.Database[currentCluster];

                if (HttpContext.Request.Query.ContainsKey("NewAlias"))
                {
                    string aliasEmail = HttpContext.Request.Query["NewAlias"];
                    if (aliasEmail.IndexOf('@') > 0) {
                        UserEntry alias = new UserEntry(new UserID(), aliasEmail, userEmail, null);
                        db.User.Add(alias);
                        await db.SaveChangesAsync();
                    }
                }
                var aliases = new List<string>();
                foreach (var user in db.User)
                {
                    if(user.Alias == userEmail)
                    {
                        if (userEmail == user.Email)
                        {
                            ViewData["Password"] = user.Password; 
                        }
                        else
                        {
                            aliases.Add(user.Email);
                        }
                    }
                }
                ViewData["Aliases"] = aliases;
            }

            ViewData["Email"] = userEmail;
            ViewData["Account"] = GetAccountType(HttpContext.Session.GetString("isAuthorized") == "true", HttpContext.Session.GetString("isAdmin") == "true");
            AddViewData();
            return View();
        }
        
        private string GetAccountType(bool isAuthorized, bool isAdmin)
        {
           return isAuthorized ? (isAdmin ? "Admin" : "User") : "Unauthorized";
        }
#endregion

    }
}
