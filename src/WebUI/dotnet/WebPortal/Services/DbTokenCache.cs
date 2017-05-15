using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.IdentityModel.Clients.ActiveDirectory;

using WindowsAuth.models;
using WebPortal.Helper;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Options;
using Microsoft.EntityFrameworkCore;

namespace WindowsAuth.Services
{
    public class PerWebUserCache
    {
        [Key]
        public int EntryId { get; set; }
        public string webUserUniqueId { get; set; }
        public byte[] cacheBits { get; set; }
        public DateTime LastWrite { get; set; }
    }
    public class DbTokenCache : TokenCache, IAzureAdTokenService
    {
        private WebAppContext _db;
        private string _userId;
        private PerWebUserCache _cache;
        private bool _useAaD;
        private OpenIDAuthentication _config;
        private AuthenticationContext _authContext;
        private ClientCredential _appCredentials;
        private IHttpContextAccessor _httpContextAccessor; 

        public DbTokenCache(WebAppContext db, IHttpContextAccessor httpContextAccessor)
        {
            this.BeforeAccess = BeforeAccessNotification;
            this.AfterAccess = AfterAccessNotification;
            this.BeforeWrite = BeforeWriteNotification;

            _db = db;
            db.Database.EnsureCreated();
            _httpContextAccessor = httpContextAccessor;
        }

        private void GetClientCredential()
        {
            var scheme = Startup.GetAuthentication(_httpContextAccessor.HttpContext.Session.GetString("Username"), out _config);
            if (!Object.ReferenceEquals(_config, null))
            {
                if (_config._bUseAadGraph )
                {
                    _userId = _httpContextAccessor.HttpContext.User.FindFirst(Constants.ObjectIdClaimType).Value;
                    string tenantId = _httpContextAccessor.HttpContext.User.FindFirst(Constants.TenantIdClaimType).Value;

                    _authContext = new AuthenticationContext(String.Format(_config._authorityFormat, tenantId), this);
                    _appCredentials = new ClientCredential(_config._clientId, _config._clientSecret);
                    _useAaD = true; 
                }
                else
                    _useAaD = false;
            }
            else
            {
                _useAaD = false; 
            }
        }

        public async Task<string> GetAccessTokenForAadGraph()
        {
            GetClientCredential();
            if (!Object.ReferenceEquals(_config, null))
            {
                if (_config._bUseAadGraph)
                {
                    AuthenticationResult result = await _authContext.AcquireTokenSilentAsync(_config._graphBasePoint, _appCredentials, new UserIdentifier(_userId, UserIdentifierType.UniqueId));
                    if (Object.ReferenceEquals(result, null))
                        return null;
                    else
                        return result.AccessToken;
                }
                else
                    return null; 
            }
            else
                return null; 
        }

        public async Task RedeemAuthCodeForAadGraph(string code, string redirect_uri)
        {
            GetClientCredential();
            // Redeem the auth code and cache the result in the db for later use.
            if (!Object.ReferenceEquals(_config, null) && _config._bUseAadGraph )
            { 
                await _authContext.AcquireTokenByAuthorizationCodeAsync(code, new Uri(redirect_uri), _appCredentials, _config._graphBasePoint );
            }
        }

        // clean up the db
        public override void Clear()
        {
            base.Clear();
            foreach (var cacheEntry in _db.PerUserCacheList)
                _db.PerUserCacheList.Remove(cacheEntry);
            _db.SaveChanges();
        }

        // Notification raised before ADAL accesses the cache.
        // This is your chance to update the in-memory copy from the db, if the in-memory version is stale
        void BeforeAccessNotification(TokenCacheNotificationArgs args)
        {
            if (_cache == null)
            {
                // first time access
                _cache = _db.PerUserCacheList.FirstOrDefault(c => c.webUserUniqueId == _userId);
            }
            else
            {   // retrieve last write from the db
                var status = from e in _db.PerUserCacheList
                             where (e.webUserUniqueId == _userId)
                             select new
                             {
                                 LastWrite = e.LastWrite
                             };
                // if the in-memory copy is older than the persistent copy
                if (status.First().LastWrite > _cache.LastWrite)
                //// read from from storage, update in-memory copy
                {
                    _cache = _db.PerUserCacheList.FirstOrDefault(c => c.webUserUniqueId == _userId);
                }
            }
            this.Deserialize((_cache == null) ? null : _cache.cacheBits);
        }

        // Notification raised after ADAL accessed the cache.
        // If the HasStateChanged flag is set, ADAL changed the content of the cache
        void AfterAccessNotification(TokenCacheNotificationArgs args)
        {
            // if state changed
            if (this.HasStateChanged)
            {
                _cache = new PerWebUserCache
                {
                    webUserUniqueId = _userId,
                    cacheBits = this.Serialize(),
                    LastWrite = DateTime.Now
                };
                //// update the db and the lastwrite                
                _db.Entry(_cache).State = _cache.EntryId == 0 ? EntityState.Added : EntityState.Modified;
                _db.SaveChanges();
                this.HasStateChanged = false;
            }
        }

        void BeforeWriteNotification(TokenCacheNotificationArgs args)
        {
            // if you want to ensure that no concurrent write take place, use this notification to place a lock on the entry
        }
    }
}
