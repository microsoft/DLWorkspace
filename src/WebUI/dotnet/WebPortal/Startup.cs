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

using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using App.Metrics.Extensions.Middleware;
using App.Metrics.Extensions.Middleware.Abstractions;
using App.Metrics.Extensions;
using App.Metrics.Extensions.Reporting.InfluxDB;
using Microsoft.AspNetCore.Mvc;
using App.Metrics.Extensions.Reporting.InfluxDB.Client;
using App.Metrics.Configuration;
using App.Metrics.Reporting.Interfaces;
using Utils.Json;
using System.Text;
using MySql.Data.MySqlClient;


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
                .AddJsonFile("configAuth.json")
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
        static public JObject DashboardConfig = new JObject();
        private StringBuilder serviceMessages = new StringBuilder();

        // This method gets called by the runtime. Use this method to add services to the container.
        public void ConfigureServices(IServiceCollection services)
        {
            // AppMetrics. #https://al-hardy.blog/2017/04/28/asp-net-core-monitoring-with-influxdb-grafana/
            var metricsHostBuilder = services.AddMetrics(options =>
            {
                options.WithGlobalTags((globalTags, info) =>
                   {
                       globalTags.Add("app", info.EntryAssemblyName);
                       globalTags.Add("env", "stage");
                   });
            })
                .AddHealthChecks()
                .AddJsonSerialization();

            using (var stream = new FileStream("dashboardConfig.json", FileMode.Open))
            using (var reader = new StreamReader(stream))
            {
                var text = reader.ReadToEnd();
                DashboardConfig = JObject.Parse(text);
            }

            var dbName = JsonUtils.GetString("influxDB.dbName", DashboardConfig);
            var dbServer = JsonUtils.GetString("influxDB.servers", DashboardConfig);
            var dbPort = JsonUtils.GetType<int>("influxDB.port", DashboardConfig, 0);
            
            if (!String.IsNullOrEmpty(dbName) && !String.IsNullOrEmpty(dbServer))
            {
                var dbUriString = $"http://{dbServer}";
                if (dbPort != 0)
                    dbUriString += ":" + dbPort.ToString(); 
                var dbUri = new Uri(dbUriString);
                metricsHostBuilder = metricsHostBuilder.AddReporting(
                    factory =>
                    {
                        factory.AddInfluxDb(
                            new InfluxDBReporterSettings
                            {
                                InfluxDbSettings = new InfluxDBSettings(dbName, dbUri),
                                ReportInterval = TimeSpan.FromSeconds(5)
                            });
                    });
                serviceMessages.Append($"Reporting to InfluxDB at {dbUriString}\n");
            }

            metricsHostBuilder.AddMetricsMiddleware(options => options.IgnoredHttpStatusCodes = new[] { 404 });

            

            var reportSetting = new InfluxDBReporterSettings();


            // Add MVC services to the services container.
            services.AddDistributedMemoryCache(); // Adds a default in-memory implementation of IDistributedCache
            services.AddSession( options => options.IdleTimeout = TimeSpan.FromDays(14) );
            services.AddMvc(options => options.AddMetricsResourceFilter());
            //services.AddCors();
            services.Configure<AppSettings>(appSettings =>
            {
                // Typed syntax - Configuration.Get<type>("")
                // Configure may not have run at the moment, so this is console printout. 

            });
	    services.Configure<FamilyModel>(families => {});
            // Add Authentication services.
            services.AddAuthentication(sharedOptions => sharedOptions.SignInScheme = CookieAuthenticationDefaults.AuthenticationScheme);

            // Expose Azure AD configuration to controllers
            services.AddOptions();

            services.AddDbContext<WebAppContext>(options => options.UseSqlite(Configuration["Data:ConnectionString"]));
            services.AddSingleton<IHttpContextAccessor, HttpContextAccessor>();
	    services.AddSingleton<IFamily, FamilyModel>();
            services.AddScoped<IAzureAdTokenService, DbTokenCache>();

        }

        public ClusterContext createDatabase(string dbName, Dictionary<string,object> clusterConfig, DLCluster clusterInfo )
        {
            var provider = "AzureSQL";
            if (clusterConfig.ContainsKey("datasource"))
                provider = clusterConfig["datasource"] as string; 
            Console.WriteLine($"Provider=={provider}, config={clusterConfig}");
            switch( provider )
            {
                case "AzureSQL":
                    { 
                        var connectionUsers = String.Format("Server={0};Database={1};User Id={2};Password={3};", // Trusted_Connection=True;MultipleActiveResultSets=true",
                                    clusterInfo.SQLHostname,
                                    dbName,
                                    clusterInfo.SQLUsername,
                                    clusterInfo.SQLPassword);
                        var optionsBuilderUsers = new DbContextOptionsBuilder<ClusterContext>();
                        optionsBuilderUsers.UseSqlServer(connectionUsers);
                        var userDatabase = new ClusterContext(optionsBuilderUsers.Options);
                        // userDatabase.Database.EnsureCreated();
                        userDatabase.Database.Migrate();
                        return userDatabase;
                    }
                default:
                    { 
                        var MySQLUsername = clusterConfig["MySQLUsername"] as string;
                        var MySQLPassword = clusterConfig["MySQLPassword"] as string;
                        var MySQLPort = clusterConfig["MySQLPort"] as string;
                        var MySQLHostname = clusterConfig["MySQLHostname"] as string;
                        var connectionUsers = $"Server={MySQLHostname};Port={MySQLPort};Uid={MySQLUsername};Password={MySQLPassword};Database={dbName}";
                        Console.WriteLine($"MySQL connection string =={connectionUsers}");
                        var optionsBuilderUsers = new DbContextOptionsBuilder<ClusterContext>();
                        optionsBuilderUsers.UseMySql(connectionUsers);
                        var userDatabase = new ClusterContext(optionsBuilderUsers.Options);
                        userDatabase.Database.EnsureCreated();
                        Console.WriteLine($"MySQL database {dbName} is created.");
                        // userDatabase.Database.Migrate(); // Migrate not working for MySQL
                        return userDatabase;
                    }
            }
        }


        // This method gets called by the runtime. Use this method to configure the HTTP request pipeline.
        public void Configure(IApplicationBuilder app, IHostingEnvironment env, 
            ILoggerFactory loggerFactory, IApplicationLifetime lifetime)
        {
            // Add the console logger.
            loggerFactory.AddConsole(Configuration.GetSection("Logging")).AddDebug();
            loggerFactory.AddFile("/var/log/webui/webui-{Date}.txt");
            app.UseMetrics();
            // May need to be turned off if reporting server is not available
            app.UseMetricsReporting(lifetime);
            
            var _logger = loggerFactory.CreateLogger("Configure");

            ConfigurationParser.ParseConfiguration(loggerFactory);

            //app.UseCors(builder =>
            //    builder.AllowAnyOrigin()
            //    );

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
                if (clusterConfig.ContainsKey("smbUsername"))
                {
                    clusterInfo.smbUsername = clusterConfig["smbUsername"] as string;
                }
                else
                {
                    clusterInfo.smbUsername = "[Your default domain username]";
                }
                if (clusterConfig.ContainsKey("smbUserPassword"))
                {
                    clusterInfo.smbUserPassword = clusterConfig["smbUserPassword"] as string;
                }
                else
                {
                    clusterInfo.smbUserPassword = "[Your default domain password]";

                }
                clusterInfo.Restapi = clusterConfig["Restapi"] as string;
                clusterInfo.Grafana = clusterConfig["Grafana"] as string;
                clusterInfo.SQLDatabaseForUser = (clusterConfig["SQLDatabaseForUser"] as string) + clusterInfo.ClusterId;
                clusterInfo.SQLHostname = clusterConfig["SQLHostname"] as string;
                clusterInfo.SQLPassword = clusterConfig["SQLPassword"] as string;
                clusterInfo.SQLUsername = clusterConfig["SQLUsername"] as string;
                // Mount description and mount point
                if (clusterConfig.ContainsKey("mountdescription"))
                {
                    clusterInfo.MountDescription = clusterConfig["mountdescription"] as string;
                }
                else
                {
                    clusterInfo.MountDescription = "{}";
                }
                // Mount description and mount point
                if (clusterConfig.ContainsKey("mountpoints"))
                {
                    clusterInfo.MountPoints = clusterConfig["mountpoints"] as string;
                }
                else
                {
                    clusterInfo.MountPoints = "{}";
                }
                if (clusterConfig.ContainsKey("mounthomefolder"))
                {
                    var val = clusterConfig["mounthomefolder"] as string;
                    switch ( val.ToLower()[0])
                    {
                        case 'y':
                        case 't':
                            clusterInfo.MountHomeFolder = true;
                            break;
                        default:
                            clusterInfo.MountHomeFolder = false;
                            break; 
                    }
                }
                else
                {
                    clusterInfo.MountHomeFolder = true;
                }
                if (clusterConfig.ContainsKey("deploymounts"))
                {
                    clusterInfo.DeployMounts = clusterConfig["deploymounts"] as string;
                }
                else
                {
                    clusterInfo.DeployMounts = "[]";
                }

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
                /*
                var connectionUsers = String.Format("Server={0};Database={1}{2};User Id={3};Password={4};", // Trusted_Connection=True;MultipleActiveResultSets=true",
                    clusterInfo.SQLHostname,
                    clusterInfo.SQLDatabaseForUser,
                    clusterInfo.ClusterId,
                    clusterInfo.SQLUsername,
                    clusterInfo.SQLPassword);
                var optionsBuilderUsers = new DbContextOptionsBuilder<ClusterContext>();
                optionsBuilderUsers.UseSqlServer(connectionUsers);
                var userDatabase = new ClusterContext(optionsBuilderUsers.Options);
                // userDatabase.Database.EnsureCreated();
                userDatabase.Database.Migrate();
                Database[clusterName] = userDatabase; */
                Database[clusterName] = createDatabase(clusterInfo.SQLDatabaseForUser, clusterConfig, clusterInfo);
            }

            var templateDb = ConfigurationParser.GetConfiguration("MasterTemplates") as Dictionary<string, object>;
            var SQLDatabaseForTemplates = templateDb["SQLDatabaseForTemplates"] as string;
            DLCluster curInfo = new DLCluster();
            curInfo.SQLDatabaseForUser = SQLDatabaseForTemplates;
            curInfo.SQLHostname = templateDb["SQLHostname"] as string;
            curInfo.SQLPassword = templateDb["SQLPassword"] as string;
            curInfo.SQLUsername = templateDb["SQLUsername"] as string;
            /*
            templatesMaster.SQLHostname = templateDb["SQLHostname"] as string;
            templatesMaster.SQLPassword = templateDb["SQLPassword"] as string;
            templatesMaster.SQLUsername = templateDb["SQLUsername"] as string;
            var connectionTemplatesMaster = String.Format("Server={0};Database={1};User Id={2};Password={3};", // Trusted_Connection=True;MultipleActiveResultSets=true",
                templatesMaster.SQLHostname,
                templatesMaster.SQLDatabaseForTemplates,
                templatesMaster.SQLUsername,
                templatesMaster.SQLPassword);
            var optionsBuilderTemplatesMaster = new DbContextOptionsBuilder<ClusterContext>();
            optionsBuilderTemplatesMaster.UseSqlServer(connectionTemplatesMaster);
            var templateMasterDatabase = new ClusterContext(optionsBuilderTemplatesMaster.Options);
            // var created = templateMasterDatabase.Database.EnsureCreated();
            templateMasterDatabase.Database.Migrate(); */
            var templateMasterDatabase = createDatabase(SQLDatabaseForTemplates, templateDb, curInfo);

            var entryArries = templateMasterDatabase.Template.Select( x => x.Template ).ToArray();
            var dic = new Dictionary<string, bool>(StringComparer.OrdinalIgnoreCase);
            foreach (var entry in entryArries)
            {
                dic.Add(entry, true);
            }
            var nEntries = entryArries.Length;
            _logger.LogInformation("# of entries in Master-Templates: {0}", nEntries);
            MasterDatabase = templateMasterDatabase;

            var template_file = "./Master-Templates.json";

            if ( File.Exists(template_file))
            {
                int ncount = 0;
                _logger.LogInformation("Entries in template file: {0}", template_file);
                var list = new List<Tuple<string, string>>();
                using (var file = File.OpenText(template_file)) 
                using (var reader = new JsonTextReader(file))
                {
                    foreach (var templateTok in (JArray)JToken.ReadFrom(reader))
                    {
                        var template = (JObject)templateTok;
                        var TName = template["Name"].Value<string>();
                        var TJson = template["Json"].Value<string>();
                        _logger.LogInformation("{0}: {1}, {2}", ncount, TName, TJson);
                        list.Add(new Tuple< string, string>(TName, TJson));
                        ncount++;
                        // var sql = @"INSERT INTO dbo.Template (Template, Json, Type) VALUES ({0}, {1}, job)";
                        // MasterDatabase.Database.ExecuteSqlCommand(sql, TName, TJson);
                    }
                }
                if (ncount > nEntries)
                {
                    // Trigger ingestion logic
                    foreach (var entry in list)
                    {
                        if (!dic.ContainsKey(entry.Item1))
                        {
                            TemplateEntry entryAdd = new TemplateEntry(entry.Item1, null, entry.Item2, "job");
                            try { 
                                MasterDatabase.Template.Add(entryAdd);
                                _logger.LogInformation($"Add {entry.Item1} to template.");
                            } catch (Exception ex )
                            {
                                _logger.LogInformation($"Failed to add {entry.Item1}, already exist in template.");
                            }
                        }
                    }
                    MasterDatabase.SaveChanges(); 
                }

	        }

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
            cookieOpt.ExpireTimeSpan = TimeSpan.FromDays(14);
            cookieOpt.SlidingExpiration = true;
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

            app.Use(async (context, next) =>
            {
                if (context.Request.Query.ContainsKey("team") && context.Session.GetString("Teams") != null)
                {
                    var team = context.Request.Query["Team"];
                    var teams = JsonConvert.DeserializeObject<string[]>(context.Session.GetString("Teams"));
                    if (Array.Exists(teams, t => t.Equals(team)))
                    {
                        context.Session.SetString("Team", team);
                        var teamClusters = await Controllers.HomeController.GetTeamClusters(context, team);
                        context.Session.SetString("TeamClusters", JsonConvert.SerializeObject(teamClusters));
                        _logger.LogInformation("{0} switch team to {1}", context.Session.GetString("Username"), team);
                    }
                }
                await next.Invoke();
            });
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
