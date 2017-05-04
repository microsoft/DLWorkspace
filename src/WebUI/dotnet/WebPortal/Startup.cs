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
                builder.AddJsonFile("userconfig.json");
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
                appSettings.restapi = Configuration["restapi"];
                appSettings.workFolderAccessPoint = Configuration["WorkFolderAccessPoint"];
                appSettings.dataFolderAccessPoint = Configuration["DataFolderAccessPoint"];
                appSettings.adminGroups = Configuration["AdminGroups"].Split(new char[] { ',', ';' }).ToList<string>();
                appSettings.authorizedGroups = Configuration["AuthorizedGroups"].Split(new char[] { ',', ';' }).ToList<string>();
            });
            // Add Authentication services.
            services.AddAuthentication(sharedOptions => sharedOptions.SignInScheme = CookieAuthenticationDefaults.AuthenticationScheme);
        }

        // This method gets called by the runtime. Use this method to configure the HTTP request pipeline.
        public void Configure(IApplicationBuilder app, IHostingEnvironment env, ILoggerFactory loggerFactory)
        {
            // Add the console logger.
            loggerFactory.AddConsole(Configuration.GetSection("Logging")).AddDebug();

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
            foreach (var scope in Configuration["AzureAd:Scope"].Split(new char[] { ' ' }))
            {
                openIDOpt.Scope.Add(scope);
            }
            openIDOpt.Authority = String.Format(Configuration["AzureAd:AadInstance"], Configuration["AzureAd:Tenant"]);
            // openIDOpt.Authority = Configuration["AzureAd:Oauth2Instance"];

            openIDOpt.PostLogoutRedirectUri = Configuration["AzureAd:PostLogoutRedirectUri"];
      
            openIDOpt.Events = new OpenIdConnectEvents
            {
                OnRemoteFailure = OnAuthenticationFailed,
                OnAuthorizationCodeReceived = OnAuthorizationCode, 
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

        private Task OnAuthorizationCode(AuthorizationCodeReceivedContext context)
        {
            context.HandleResponse();
            var info = context.ToString();
            return Task.FromResult(0);
        }

        /*

                            Notifications = new OpenIdConnectAuthenticationNotifications
                            {
                                AuthorizationCodeReceived = async (context) =>
                                {
                                    var code = context.Code;
                                    string signedInUserID = context.AuthenticationTicket.Identity.FindFirst(ClaimTypes.NameIdentifier).Value;
                                    ConfidentialClientApplication cca = new ConfidentialClientApplication(
                                        appId,
                                        redirectUri,
                                        new ClientCredential(appSecret),
                                        new SessionTokenCache(signedInUserID, context.OwinContext.Environment["System.Web.HttpContextBase"] as HttpContextBase));
                                    string[] scopes = graphScopes.Split(new char[] { ' ' });

                                    AuthenticationResult result = await cca.AcquireTokenByAuthorizationCodeAsync(scopes, code);
                                },
                                AuthenticationFailed = (context) =>
                                {
                                    context.HandleResponse();
                                    context.Response.Redirect("/Error?message=151561651" + context.Exception.Message);
                                    return Task.FromResult(0);
                                }
                            }
                            */

    }
}
