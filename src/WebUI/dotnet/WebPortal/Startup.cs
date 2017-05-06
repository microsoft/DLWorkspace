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
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Microsoft.IdentityModel.Protocols.OpenIdConnect;
using WindowsAuth.models;

using WebPortal.Helper;
using Serilog.Extensions.Logging;
using Microsoft.IdentityModel.Clients.ActiveDirectory;
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
            if (File.Exists("userconfig.json"))
                builder.AddJsonFile("userconfig.json", optional: true, reloadOnChange: true);
            Configuration = builder.Build();
            
        }

        static public IConfigurationRoot Configuration { get; set; }

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
            //cookieOpt.CookieName = "dlws-auth";
            //cookieOpt.CookieSecure = Microsoft.AspNetCore.Http.CookieSecurePolicy.Always;
            //cookieOpt.AuthenticationScheme = "Cookies";
            app.UseCookieAuthentication(cookieOpt);

            var openIDOpt = new OpenIdConnectOptions();
            openIDOpt.ClientId = Configuration["AzureAD:ClientId"];
            openIDOpt.ClientSecret = Configuration["AzureAD:ClientSecret"];
            
            foreach (var scope in Configuration["AzureAd:Scope"].Split(new char[] { ' ' }))
            {
                openIDOpt.Scope.Add(scope);
            }
            openIDOpt.Authority = String.Format(Configuration["AzureAd:AadInstance"], Configuration["AzureAd:Tenant"]);
            // openIDOpt.Authority = Configuration["AzureAd:Oauth2Instance"];

            openIDOpt.PostLogoutRedirectUri = Configuration["AzureAd:PostLogoutRedirectUri"];
            // openIDOpt.ResponseType = OpenIdConnectResponseType.CodeIdToken;
            openIDOpt.GetClaimsFromUserInfoEndpoint = false; 
      
            openIDOpt.Events = new OpenIdConnectEvents
            {
                OnRemoteFailure = OnAuthenticationFailed,
                OnAuthorizationCodeReceived = OnAuthorizationCodeReceived, 
            };

            // Configure the OWIN pipeline to use OpenID Connect auth.
            app.UseOpenIdConnectAuthentication(openIDOpt);





            // Configure the OWIN pipeline to use OpenID Connect auth.

            //app.UseOpenIdConnectAuthentication(new OpenIdConnectOptions

            //{

            //    ClientId = Configuration["AzureAD:ClientId"],

            //    Authority = String.Format(Configuration["AzureAd:AadInstance"], Configuration["AzureAd:Tenant"]),

            //    PostLogoutRedirectUri = Configuration["AzureAd:PostLogoutRedirectUri"],

            //    Events = new OpenIdConnectEvents

            //    {

            //        OnRemoteFailure = OnAuthenticationFailed,

            //    }

            //});

            app.UseSession();
            // Configure MVC routes
            app.UseMvc(routes =>
            {
                routes.MapRoute(
                    name: "default",
                    template: "{controller=Home}/{action=Index}/{id?}");
            });
        }

        // Handle sign-in errors differently than generic errors.
        private Task OnAuthenticationFailed(FailureContext context)
        {
            context.HandleResponse();
            context.Response.Redirect("/Home/Error?message=" + context.Failure.Message);
            return Task.FromResult(0);
        }

        private async Task OnAuthorizationCodeReceived(AuthorizationCodeReceivedContext context)
        {
            string userObjectId = (context.Ticket.Principal.FindFirst("http://schemas.microsoft.com/identity/claims/objectidentifier"))?.Value;
            var ClientId = Configuration["AzureAD:ClientId"];
            var ClientSecret = Configuration["AzureAD:ClientSecret"];
            ClientCredential clientCred = new ClientCredential(ClientId, ClientSecret);
            var Authority = String.Format(Configuration["AzureAd:AadInstance"], Configuration["AzureAd:Tenant"]);
            var GraphResourceId = Configuration["AzureAD:AzureResourceURL"]; 
            AuthenticationContext authContext = new AuthenticationContext(Authority, new NaiveSessionCache(userObjectId, context.HttpContext.Session));
            AuthenticationResult authResult = await authContext.AcquireTokenByAuthorizationCodeAsync(
                context.ProtocolMessage.Code, new Uri(context.Properties.Items[OpenIdConnectDefaults.RedirectUriForCodePropertiesKey]), clientCred, GraphResourceId);

            context.HandleCodeRedemption(); 
        }

    }
}
