using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.IdentityModel.Clients.ActiveDirectory;

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
        private TodoListWebAppContext _db;
        private string _userId;
        private AzureADConfig _aadConfig;
        private PerWebUserCache _cache;
        private AuthenticationContext _authContext;
        private readonly ClientCredential _appCredentials;

        public DbTokenCache(TodoListWebAppContext db, IHttpContextAccessor httpContextAccessor, IOptions<AzureADConfig> aadConfig)
        {
            this.BeforeAccess = BeforeAccessNotification;
            this.AfterAccess = AfterAccessNotification;
            this.BeforeWrite = BeforeWriteNotification;

            _db = db;
            _aadConfig = aadConfig.Value;
            _userId = httpContextAccessor.HttpContext.User.FindFirst(AzureADConstants.ObjectIdClaimType).Value;
            string tenantId = httpContextAccessor.HttpContext.User.FindFirst(AzureADConstants.TenantIdClaimType).Value;
            _authContext = new AuthenticationContext(String.Format(_aadConfig.AuthorityFormat, tenantId), this);
            _appCredentials = new ClientCredential(_aadConfig.ClientId, _aadConfig.ClientSecret);
        }

        public async Task<string> GetAccessTokenForAadGraph()
        {
            AuthenticationResult result = await _authContext.AcquireTokenSilentAsync(_aadConfig.GraphResourceId, _appCredentials, new UserIdentifier(_userId, UserIdentifierType.UniqueId));
            return result.AccessToken;
        }

        public async Task RedeemAuthCodeForAadGraph(string code, string redirect_uri)
        {
            // Redeem the auth code and cache the result in the db for later use.
            await _authContext.AcquireTokenByAuthorizationCodeAsync(code, new Uri(redirect_uri), _appCredentials, _aadConfig.GraphResourceId);
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
