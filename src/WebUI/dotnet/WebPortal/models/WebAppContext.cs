using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.EntityFrameworkCore;
using WindowsAuth.Services;

namespace WindowsAuth.models
{
    public class WebAppContext : DbContext
    {
        public DbSet<WebPortalEntity> Todoes { get; set; }
        public DbSet<Tenant> Tenants { get; set; }
        public DbSet<AADUserRecord> Users { get; set; }
        public DbSet<PerWebUserCache> PerUserCacheList { get; set; }

        public WebAppContext(DbContextOptions<WebAppContext> options) : base(options) { }

        protected override void OnModelCreating(ModelBuilder builder)
        {
            base.OnModelCreating(builder);
        }
    }
}
