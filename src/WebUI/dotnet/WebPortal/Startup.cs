using System;
using System.IO; 
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Authentication.OpenIdConnect;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Options;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Microsoft.IdentityModel.Protocols.OpenIdConnect;
using System.Security.Claims;
using WindowsAuth.models;
using WindowsAuth.Services;
using WebPortal.Helper;


using Serilog.Extensions.Logging;
using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.Clients.ActiveDirectory;
using Microsoft.IdentityModel.Tokens;
using Microsoft.AspNetCore.Http;


namespace WindowsAuth
{
    public class Startup
    {
        public Startup(IHostingEnvironment env)
        {
            // Set up configuration sources.
            var builder = new ConfigurationBuilder()
                .SetBasePath(env.ContentRootPath)
                .AddJsonFile("config.json")
                .AddJsonFile("appsettings.json", optional: true, reloadOnChange: true);

            // User Configuration is added through ./deploy.py
            try
            {
                using (var fp = File.Open("userconfig.json", FileMode.Open, FileAccess.Read))
                {
                }
                builder.AddJsonFile("userconfig.json", optional: true, reloadOnChange: true);
            }
            catch { };
            Configuration = builder.Build();

        }

        static public IConfigurationRoot Configuration { get; set; }
        static public Dictionary<string, OpenIDAuthentication> AuthenticationSchemes;
        static public Dictionary<string, DLCluster> Clusters; 
        static public Dictionary<string, ClusterContext> Database;
        static public ClusterContext MasterDatabase;

        // This method gets called by the runtime. Use this method to add services to the container.
        public void ConfigureServices(IServiceCollection services)
        {
            // Add MVC services to the services container.
            services.AddMvc();
            services.AddDistributedMemoryCache(); // Adds a default in-memory implementation of IDistributedCache
            services.AddSession();

            services.Configure<AppSettings>(appSettings =>
            {
                // Typed syntax - Configuration.Get<type>("")
                // Configure may not have run at the moment, so this is console printout. 

            });
            // Add Authentication services.
            services.AddAuthentication(sharedOptions => sharedOptions.SignInScheme = CookieAuthenticationDefaults.AuthenticationScheme);

            // Expose Azure AD configuration to controllers
            services.AddOptions();

            services.AddDbContext<WebAppContext>(options => options.UseSqlite(Configuration["Data:ConnectionString"]));
            services.AddSingleton<IHttpContextAccessor, HttpContextAccessor>();
            services.AddScoped<IAzureAdTokenService, DbTokenCache>();

        }



        // This method gets called by the runtime. Use this method to configure the HTTP request pipeline.
        public void Configure(IApplicationBuilder app, IHostingEnvironment env, ILoggerFactory loggerFactory)
        {
            // Add the console logger.
            loggerFactory.AddConsole(Configuration.GetSection("Logging")).AddDebug();
            loggerFactory.AddFile("/var/log/webui/webui-{Date}.txt");

            var _logger = loggerFactory.CreateLogger("Configure");

            ConfigurationParser.ParseConfiguration(loggerFactory);
            var clusters = ConfigurationParser.GetConfiguration("DLClusters") as Dictionary<string, object>;
            if ( Object.ReferenceEquals(clusters, null ))
            {
                throw new ArgumentException("There are no DLClusters in the configuration file");
            }
            Clusters = new Dictionary<string, DLCluster>();
            Database = new Dictionary<string, ClusterContext>();
            string defaultClusterName = null; 
            foreach (var pair in clusters)
            {
                var clusterName = pair.Key;
                var clusterConfig = pair.Value as Dictionary<string, object>;
                _logger.LogInformation("Configure cluster {0}", clusterName);
                if (Object.ReferenceEquals(clusterConfig, null))
                {
                    throw new ArgumentException("Configuration for cluster {0} is not provided as a JSon dictionary", clusterName );
                }
                var clusterInfo = new DLCluster();
                clusterInfo.ClusterName = clusterName;
                clusterInfo.ClusterId = clusterConfig["ClusterId"] as string;
                if (clusterConfig.ContainsKey("AdminGroups"))
                { 
                    var lst = ConfigurationParser.ParseConfigurationAsList(clusterConfig["AdminGroups"]);
                    // Convert to Dictionary for fast checkin
                    clusterInfo.AdminGroups = new Dictionary<string, bool>(StringComparer.OrdinalIgnoreCase);
                    foreach( var group in lst )
                    {
                        clusterInfo.AdminGroups[group] = true;
                    }
                }
                else
                    clusterInfo.AdminGroups = new Dictionary<string, bool>();
                if (clusterConfig.ContainsKey("AuthorizedGroups"))
                {
                    var lst = ConfigurationParser.ParseConfigurationAsList(clusterConfig["AuthorizedGroups"]);
                    clusterInfo.AuthorizedGroups = new Dictionary<string, bool>(StringComparer.OrdinalIgnoreCase);
                    foreach (var group in lst)
                    {
                        clusterInfo.AuthorizedGroups[group] = true; 
                    }
                }
                else
                    clusterInfo.AuthorizedGroups = new Dictionary<string, bool>();
                if (clusterConfig.ContainsKey("RegisterGroups"))
                {
                    var lst = ConfigurationParser.ParseConfigurationAsList(clusterConfig["RegisterGroups"]);
                    clusterInfo.RegisterGroups = new Dictionary<string, bool>(StringComparer.OrdinalIgnoreCase);
                    foreach (var group in lst)
                    {
                        clusterInfo.RegisterGroups[group] = true;
                    }
                }
                else
                    clusterInfo.RegisterGroups = new Dictionary<string, bool>();

                clusterInfo.DataFolderAccessPoint = clusterConfig["DataFolderAccessPoint"] as string;
                clusterInfo.WorkFolderAccessPoint = clusterConfig["WorkFolderAccessPoint"] as string;
                clusterInfo.Restapi = clusterConfig["Restapi"] as string;
                clusterInfo.SQLDatabaseForUser = clusterConfig["SQLDatabaseForUser"] as string;
                clusterInfo.SQLHostname = clusterConfig["SQLHostname"] as string;
                clusterInfo.SQLPassword = clusterConfig["SQLPassword"] as string;
                clusterInfo.SQLUsername = clusterConfig["SQLUsername"] as string;
                var isDefault = clusterConfig.ContainsKey("Default") && (clusterConfig["Default"] as string).ToLower()=="true";
                if (isDefault)
                    defaultClusterName = clusterName;
                _logger.LogDebug("ClusterId: {0}", clusterInfo.ClusterId);
                _logger.LogDebug("DataFolderAccessPoint: {0}", clusterInfo.DataFolderAccessPoint);
                _logger.LogDebug("WorkFolderAccessPoint: {0}", clusterInfo.WorkFolderAccessPoint);
                _logger.LogDebug("Restapi: {0}", clusterInfo.Restapi);
                _logger.LogDebug("SQLDatabaseForUser: {0}", clusterInfo.SQLDatabaseForUser);
                _logger.LogDebug("SQLHostname: {0}", clusterInfo.SQLHostname);
                _logger.LogDebug("SQLPassword: {0}", clusterInfo.SQLPassword);
                _logger.LogDebug("SQLUsername: {0}", clusterInfo.SQLUsername);
                Clusters[clusterName] = clusterInfo;
                var connectionUsers = String.Format("Server={0};Database={1}{2};User Id={3};Password={4}",
                    clusterInfo.SQLHostname,
                    clusterInfo.SQLDatabaseForUser,
                    clusterInfo.ClusterId,
                    clusterInfo.SQLUsername,
                    clusterInfo.SQLPassword);
                var optionsBuilderUsers = new DbContextOptionsBuilder<ClusterContext>();
                optionsBuilderUsers.UseSqlServer(connectionUsers);
                var userDatabase = new ClusterContext(optionsBuilderUsers.Options);
                userDatabase.Database.EnsureCreated();
                Database[clusterName] = userDatabase;
            }

            var templateDb = ConfigurationParser.GetConfiguration("MasterTemplates") as Dictionary<string, object>;
            var templatesMaster = new TemplateDatabase();
            templatesMaster.SQLDatabaseForTemplates = templateDb["SQLDatabaseForTemplates"] as string;
            templatesMaster.SQLHostname = templateDb["SQLHostname"] as string;
            templatesMaster.SQLPassword = templateDb["SQLPassword"] as string;
            templatesMaster.SQLUsername = templateDb["SQLUsername"] as string;
            var connectionTemplatesMaster = String.Format("Server={0};Database={1};User Id={2};Password={3}",
                templatesMaster.SQLHostname,
                templatesMaster.SQLDatabaseForTemplates,
                templatesMaster.SQLUsername,
                templatesMaster.SQLPassword);
            var optionsBuilderTemplatesMaster = new DbContextOptionsBuilder<ClusterContext>();
            optionsBuilderTemplatesMaster.UseSqlServer(connectionTemplatesMaster);
            var templateMasterDatabase = new ClusterContext(optionsBuilderTemplatesMaster.Options);
            templateMasterDatabase.Database.EnsureCreated();
            MasterDatabase = templateMasterDatabase;


            if (String.IsNullOrEmpty(defaultClusterName))
                defaultClusterName = Clusters.Keys.First<string>();
            Clusters[""] = Clusters[defaultClusterName];
            _logger.LogDebug("Default Cluster: {0}", defaultClusterName);

            // Configure error handling middleware.
            app.UseExceptionHandler("/Home/Error");

            // Add static files to the request pipeline.
            app.UseStaticFiles();

            // Configure the OWIN pipeline to use cookie auth.
            var cookieOpt = new CookieAuthenticationOptions();
            //cookieOpt.AutomaticAuthenticate = true;
            // cookieOpt.CookieName = "dlws-auth";
            //cookieOpt.CookieSecure = Microsoft.AspNetCore.Http.CookieSecurePolicy.Always;
            // cookieOpt.AuthenticationScheme = "Cookies";
            app.UseCookieAuthentication(cookieOpt);

            var deployAuthenticationConfig  = ConfigurationParser.GetConfiguration("DeployAuthentications") as Dictionary<string, object>;
            var deployAuthentication = new Dictionary<string, bool>(StringComparer.OrdinalIgnoreCase);
            foreach (var pair in deployAuthenticationConfig)
                deployAuthentication[pair.Value as string] = true;
            int numDeployedAuthentication = deployAuthentication.Count;

            var authentication = ConfigurationParser.GetConfiguration("Authentications") as Dictionary<string, object>;
            AuthenticationSchemes = new Dictionary<string, OpenIDAuthentication>(); 
            foreach (var pair in authentication)
            {
                bool bUse = (numDeployedAuthentication == 0 || deployAuthentication.ContainsKey(pair.Key));
                if ( bUse )
                { 
                    var authenticationScheme = pair.Key;
                    var authenticationConfig = pair.Value;
                    var openIDOpt = new OpenIDAuthentication(authenticationScheme, authenticationConfig, loggerFactory);
                    AuthenticationSchemes[authenticationScheme] = openIDOpt;
                    app.UseOpenIdConnectAuthentication(openIDOpt);
                }
            }
            
            // Configure the OWIN pipeline to use OpenID Connect auth.
            app.UseSession();
            // Configure MVC routes
            app.UseMvc(routes =>
            {
                routes.MapRoute(
                    name: "default",
                    template: "{controller=Home}/{action=Index}/{id?}");
            });
        }

        public static string GetAuthentication(string email, out OpenIDAuthentication config )
        {
            foreach (var pair in AuthenticationSchemes)
            {
                if (pair.Value.isAuthentication(email))
                {
                    config = pair.Value;
                    return pair.Key; 
                }
            }
            config = null;
            return OpenIdConnectDefaults.AuthenticationScheme; 
        }


    }

}
