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
                appSettings.restapi = Configuration["Restapi"];
                appSettings.workFolderAccessPoint = Configuration["WorkFolderAccessPoint"];
                appSettings.dataFolderAccessPoint = Configuration["DataFolderAccessPoint"];
                appSettings.adminGroups = ConfigurationParser.GetConfigurationAsList("AdminGroups"); //  Configuration["AdminGroups"].Split(new char[] { ',', ';' }).ToList<string>();
                appSettings.authorizedGroups = ConfigurationParser.GetConfigurationAsList("AuthorizedGroups"); // Configuration["AuthorizedGroups"].Split(new char[] { ',', ';' }).ToList<string>();
                // Configure may not have run at the moment, so this is console printout. 
                // Console.WriteLine("Authorization group is: {0}", appSettings.authorizedGroups);
                // Console.WriteLine("AdminGroups group is: {0}", appSettings.adminGroups);

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

            var authentication = ConfigurationParser.GetConfiguration("Authentications") as Dictionary<string, object>;
            AuthenticationSchemes = new Dictionary<string, OpenIDAuthentication>(); 
            foreach (var pair in authentication)
            {
                var authenticationScheme = pair.Key;
                var authenticationConfig = pair.Value;
                var openIDOpt = new OpenIDAuthentication(authenticationScheme, authenticationConfig, loggerFactory);
                AuthenticationSchemes[authenticationScheme] = openIDOpt;
                app.UseOpenIdConnectAuthentication(openIDOpt);
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
