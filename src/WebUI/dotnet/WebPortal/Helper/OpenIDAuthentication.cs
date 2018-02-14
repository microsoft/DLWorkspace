using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.OpenIdConnect;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Http;
using WindowsAuth.models;
using WindowsAuth.Services;
using WindowsAuth;
using Microsoft.IdentityModel.Clients.ActiveDirectory;
using System.Security.Claims;
using Microsoft.IdentityModel.Protocols.OpenIdConnect;
using Microsoft.Extensions.Logging;

namespace WebPortal.Helper
{
    public class OpenIDAuthentication: OpenIdConnectOptions
    {
        private readonly string _authenticationScheme = null;
        private readonly Dictionary<string, object> _config = null; 

        public bool _bUseAadGraph = false;
        public bool _bUseToken = false;
        public bool _bUseIdToken = false; 
        public string _displayName = null;
        public string _clientId = null;
        public string _clientSecret = null;
        public string _authorityFormat = null;
        public string _tenant = null;
        public string _AadResourceURL = null;
        public string _scope = null;
        public string _redirectURL = "";
        public string _graphBasePoint = null;
        public string _graphApiVersion = null;
        public Dictionary<string, object> _domains = null; 
        public readonly ILogger _logger; 

        public OpenIDAuthentication( string authenticationScheme, object config, ILoggerFactory logger) 
        {
            _logger = logger.CreateLogger("Authentication(" + authenticationScheme +")");
            _authenticationScheme = authenticationScheme;
            _config = config as Dictionary<string, object>;
            if (Object.ReferenceEquals(_config, null))
                throw new System.ArgumentException(String.Format("Authentication {0}, there is no valid configuration object {1}", authenticationScheme, config));
            if (_config.ContainsKey("UseAadGraph") &&
                String.Compare(_config["UseAadGraph"] as string, "true", true) == 0)
                _bUseAadGraph = true;
            else
                _bUseAadGraph = false;
            if (_config.ContainsKey("UseToken") &&
               String.Compare(_config["UseToken"] as string, "true", true) == 0)
                _bUseToken = true;
            else
                _bUseToken = false;
            if (_config.ContainsKey("UseIdToken") &&
               String.Compare(_config["UseIdToken"] as string, "true", true) == 0)
                _bUseIdToken = true;
            else
                _bUseIdToken = false;


            if (_config.ContainsKey("DisplayName"))
                _displayName = _config["DisplayName"] as string;
            if (_config.ContainsKey("ClientId"))
                _clientId = _config["ClientId"] as string; 
            if (_bUseAadGraph && String.IsNullOrEmpty(_clientId))
                throw new System.ArgumentException(String.Format("Authentication {0}, there is clientId"));
            if (_config.ContainsKey("ClientSecret"))
                _clientSecret = _config["ClientSecret"] as string;
            if (_bUseAadGraph && String.IsNullOrEmpty(_clientSecret))
                throw new System.ArgumentException(String.Format("Authentication {0}, there is ClientSecret"));
            if (_config.ContainsKey("AuthorityFormat"))
                _authorityFormat = _config["AuthorityFormat"] as string;
            if ( String.IsNullOrEmpty(_authorityFormat))
                throw new System.ArgumentException(String.Format("Authentication {0}, mendatory configuration AuthorityFormat is missing."));
            if (_config.ContainsKey("Tenant"))
                _tenant = _config["Tenant"] as string;
            if (_bUseAadGraph && String.IsNullOrEmpty(_tenant))
                throw new System.ArgumentException(String.Format("Authentication {0}, mendatory configuration Tenant is missing."));
            if (_config.ContainsKey("AzureResourceURL"))
                _AadResourceURL = _config["AzureResourceURL"] as string;
            if (_config.ContainsKey("Scope"))
                _scope = _config["Scope"] as string;
            if (_config.ContainsKey("RedirectUri"))
                _redirectURL = _config["RedirectUri"] as string;
            if (_config.ContainsKey("GraphBaseEndpoint"))
                _graphBasePoint = _config["GraphBaseEndpoint"] as string;
            if (_bUseAadGraph && String.IsNullOrEmpty(_graphBasePoint))
                throw new System.ArgumentException(String.Format("Authentication {0}, need GraphBaseEndpoint."));
            if (_config.ContainsKey("GraphApiVersion"))
                _graphApiVersion = _config["GraphApiVersion"] as string;
            if (_bUseAadGraph && String.IsNullOrEmpty(_graphApiVersion))
                throw new System.ArgumentException(String.Format("Authentication {0}, need GraphApiVersion."));
            if (_config.ContainsKey("Domains"))
                _domains = _config["Domains"] as Dictionary<string, object>;

            _logger.LogInformation("Use AadGraph {0}, ClientId {1}, ClientSecret{2}, AuthorityFormat {3}, Tenant {4}, AzureResourceURL {5}, Scope {6}, RedirectURL {7}, GraphBaseEndpoint {8}, GraphApiVersion {9}",
                _bUseAadGraph, _clientId, _clientSecret,
                _authorityFormat, _tenant, _AadResourceURL, _scope, _redirectURL,
                _graphBasePoint, _graphApiVersion);

            AuthenticationScheme = _authenticationScheme;
            ClientId = _clientId;
            DisplayName = _displayName;
            CallbackPath = new PathString(  "/signin-" + _authenticationScheme );
            // AutomaticChallenge = true;

            if ( !String.IsNullOrEmpty(_clientSecret))
                ClientSecret = _clientSecret;

            if ( !String.IsNullOrEmpty(_scope))
            {
                foreach (var scope in _scope.Split(new char[] { ' ' }))
                {
                    Scope.Add(scope);
                }
            }
            if (_bUseAadGraph || _bUseToken )
                ResponseType = OpenIdConnectResponseType.CodeIdToken;
            if ( _bUseIdToken ) 
                ResponseType = OpenIdConnectResponseType.IdToken; 

            Authority = String.Format(_authorityFormat, _tenant);

            PostLogoutRedirectUri = "/";
            GetClaimsFromUserInfoEndpoint = true;
            /*
            openIDOpt.TokenValidationParameters = new TokenValidationParameters
            {
                // instead of using the default validation (validating against a single issuer value, as we do in line of business apps), 
                // we inject our own multitenant validation logic
                ValidateIssuer = false
            };*/

            var ev = new OpenIdConnectEvents();
            if (_bUseAadGraph)
            {
                ev.OnAuthorizationCodeReceived = OnAuthorizationCodeReceived;
                ev.OnRedirectToIdentityProvider = OnRedirectToIdentityProvider;
            }
            if ( _bUseAadGraph || _bUseToken || _bUseIdToken )
                ev.OnTokenValidated = OnTokenValidated;

            ev.OnRemoteFailure = OnAuthenticationFailed;



            Events = ev;
        }

        public bool isAuthentication(string email )
        {
            foreach ( var pair in _domains )
            {
                var domain = pair.Value as string;
                if (email.IndexOf(domain, StringComparison.OrdinalIgnoreCase) >= 0)
                    return true; 
            }
            return false; 
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
            if (_bUseAadGraph)
            {
                string adminConsentSignUp = null;
                if (context.Request.Path == new PathString("/Account/SignUp") && context.Properties.Items.TryGetValue(Constants.AdminConsentKey, out adminConsentSignUp))
                {
                    if (adminConsentSignUp == Constants.True)
                    {
                        context.ProtocolMessage.Prompt = "admin_consent";
                    }
                }
                context.ProtocolMessage.Prompt = "admin_consent";
            }
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
            ClientCredential clientCred = new ClientCredential(_clientId, _clientSecret);
            var Authority = String.Format(_authorityFormat, _tenant);
            var GraphResourceId = _AadResourceURL;
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

