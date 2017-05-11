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

            // Expose Azure AD configuration to controllers
            services.AddOptions();

            services.AddDbContext<WebAppContext>( options => options.UseSqlite(Configuration["Data:ConnectionString"]));
            services.AddSingleton<IHttpContextAccessor, HttpContextAccessor>();
            services.AddScoped<IAzureAdTokenService, DbTokenCache>();

            var azureADMultiTenant = Configuration.GetChildren().Where(c => c.Key.Equals("AzureAdMultiTenant")).First();
            // var azureADMultiTenant = Configuration.GetSection("AzureAdMultiTenant");
            services.Configure<AzureADConfig>(azureADMultiTenant);


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
            openIDOpt.AutomaticChallenge = true;
            openIDOpt.ClientId = Configuration["AzureAdMultiTenant:ClientId"];
            openIDOpt.ClientSecret = Configuration["AzureAdMultiTenant:ClientSecret"];

            foreach (var scope in Configuration["AzureAd:Scope"].Split(new char[] { ' ' }))
            {
                openIDOpt.Scope.Add(scope);
            }
            openIDOpt.Authority = String.Format(Configuration["AzureAd:AadInstance"], Configuration["AzureAd:Tenant"]);
            // openIDOpt.Authority = Configuration["AzureAd:Oauth2Instance"];

            openIDOpt.PostLogoutRedirectUri = Configuration["AzureAd:PostLogoutRedirectUri"];
            // openIDOpt.ResponseType = OpenIdConnectResponseType.CodeIdToken;
            openIDOpt.GetClaimsFromUserInfoEndpoint = false;
            openIDOpt.TokenValidationParameters = new TokenValidationParameters
            {
                // instead of using the default validation (validating against a single issuer value, as we do in line of business apps), 
                // we inject our own multitenant validation logic
                ValidateIssuer = false
            };
        


            openIDOpt.Events = new OpenIdConnectEvents
            {
                OnRemoteFailure = OnAuthenticationFailed,
                OnAuthorizationCodeReceived = OnAuthorizationCodeReceived,
                OnTokenValidated = OnTokenValidated,
                OnRedirectToIdentityProvider = OnRedirectToIdentityProvider
            };

            // Configure the OWIN pipeline to use OpenID Connect auth.
            app.UseOpenIdConnectAuthentication(openIDOpt);

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

        private Task OnRedirectToIdentityProvider(RedirectContext context)
        {
            // Using examples from: https://github.com/jinlmsft/active-directory-webapp-webapi-multitenant-openidconnect-aspnetcore

            string adminConsentSignUp = null;
            if (context.Request.Path == new PathString("/Account/SignUp") && context.Properties.Items.TryGetValue(Constants.AdminConsentKey, out adminConsentSignUp))
            {
                if (adminConsentSignUp == Constants.True)
                {
                    context.ProtocolMessage.Prompt = "admin_consent";
                }
            }
            context.ProtocolMessage.Prompt = "admin_consent";
            return Task.FromResult(0);
        }

        // Redeem the auth code for a token to the Graph API and cache it for later.
        private async Task OnAuthorizationCodeReceived(AuthorizationCodeReceivedContext context)
        {
            // Redeem auth code for access token and cache it for later use
            context.HttpContext.User = context.Ticket.Principal;
            IAzureAdTokenService tokenService = (IAzureAdTokenService)context.HttpContext.RequestServices.GetService(typeof(IAzureAdTokenService));
            await tokenService.RedeemAuthCodeForAadGraph(context.ProtocolMessage.Code, context.Properties.Items[OpenIdConnectDefaults.RedirectUriForCodePropertiesKey]);

            // Notify the OIDC middleware that we already took care of code redemption.
            context.HandleCodeRedemption();
        }

        private async Task OnAuthorizationCodeReceivedExp(AuthorizationCodeReceivedContext context)
        {
            string userObjectId = (context.Ticket.Principal.FindFirst("http://schemas.microsoft.com/identity/claims/objectidentifier"))?.Value;
            var ClientId = Configuration["AzureAdMultiTenant:ClientId"];
            var ClientSecret = Configuration["AzureAdMultiTenant:ClientSecret"];
            ClientCredential clientCred = new ClientCredential(ClientId, ClientSecret);
            var Authority = String.Format(Configuration["AzureAd:AadInstance"], Configuration["AzureAd:Tenant"]);
            var GraphResourceId = Configuration["AzureAD:AzureResourceURL"]; 
            AuthenticationContext authContext = new AuthenticationContext(Authority, new NaiveSessionCache(userObjectId, context.HttpContext.Session));
            AuthenticationResult authResult = await authContext.AcquireTokenByAuthorizationCodeAsync(
                context.ProtocolMessage.Code, new Uri(context.Properties.Items[OpenIdConnectDefaults.RedirectUriForCodePropertiesKey]), clientCred, GraphResourceId);

            context.HandleCodeRedemption(); 
        }

        // Inject custom logic for validating which users we allow to sign in
        // Here we check that the user (or their tenant admin) has signed up for the application.
        private Task OnTokenValidated(TokenValidatedContext context)
        {
            // Retrieve caller data from the incoming principal
            string issuer = context.Ticket.Principal.FindFirst(Constants.Issuer).Value;
            string objectID = context.Ticket.Principal.FindFirst(Constants.ObjectIdClaimType).Value;
            string tenantID = context.Ticket.Principal.FindFirst(Constants.TenantIdClaimType).Value;
            string upn = "";
            var upnPnt = context.Ticket.Principal.FindFirst(ClaimTypes.Upn);
            if (!Object.ReferenceEquals(upnPnt, null))
            {
                upn = upnPnt.Value;
            }
            else
            {
                var emailPnt = context.Ticket.Principal.FindFirst(ClaimTypes.Email);
                if (!Object.ReferenceEquals(emailPnt, null))
                {
                    upn = emailPnt.Value;
                }
            }

            WebAppContext db = (WebAppContext)context.HttpContext.RequestServices.GetService(typeof(WebAppContext));
            db.Database.EnsureCreated();
            // If the user is signing up, add the user or tenant to the database record of sign ups.
            Tenant tenant = db.Tenants.FirstOrDefault(a => a.IssValue.Equals(issuer));
            AADUserRecord user = db.Users.FirstOrDefault(b => b.ObjectID.Equals(objectID));
            
            string adminConsentSignUp = null;
            if (context.Properties.Items.TryGetValue(Constants.AdminConsentKey, out adminConsentSignUp))
            {
                if (adminConsentSignUp == Constants.True)
                {
                    if (tenant == null)
                    {
                        tenant = new Tenant { Created = DateTime.Now, IssValue = issuer, Name = context.Properties.Items[Constants.TenantNameKey], AdminConsented = true };
                        db.Tenants.Add(tenant);
                    }
                    else
                    {
                        tenant.AdminConsented = true;
                    }
                }
                else if (user == null)
                {
                    user = new AADUserRecord { UPN = upn, ObjectID = objectID };
                    db.Users.Add(user);
                }
                db.SaveChanges();
            }

            // Ensure that the caller is recorded in the db of users who went through the individual onboarding
            // or if the caller comes from an admin-consented, recorded issuer.
            if ((tenant == null || !tenant.AdminConsented) && (user == null))
            {
                // If not, the caller was neither from a trusted issuer or a registered user - throw to block the authentication flow
                // throw new SecurityTokenValidationException("Did you forget to sign-up?");
            }

            return Task.FromResult(0);
        }

    }
}
