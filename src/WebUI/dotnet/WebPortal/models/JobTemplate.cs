using Microsoft.EntityFrameworkCore;
using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.Linq;
using System.Threading.Tasks;

namespace WindowsAuth.models
{
    public partial class TemplateContext : DbContext
    {
        /*
        private string _connectionString; 
        public UserContext(string connectionString )
        {
            _connectionString = connectionString;
        }
        protected override void OnConfiguring(DbContextOptionsBuilder optionsBuilder)
        {
            optionsBuilder.UseSqlServer(_connectionString);
            
        } */
        public TemplateContext(DbContextOptions<TemplateContext> options) : base(options) { }

        protected override void OnModelCreating(ModelBuilder builder)
        {
            base.OnModelCreating(builder);

            // Configure Asp Net Identity Tables
            builder.Entity<TemplateEntry>().ToTable("Template");
            builder.Entity<TemplateEntry>().HasKey(c => c.Template);
            builder.Entity<TemplateEntry>().Property(u => u.Template).HasMaxLength(128);
            builder.Entity<TemplateEntry>().Property(u => u.Username).HasMaxLength(128);
            builder.Entity<TemplateEntry>().Property(u => u.Json);
        }
        public virtual DbSet<TemplateEntry> Template { get; set; }
    }

    /// <summary>
    /// User entry class in Database
    /// </summary>
    public partial class TemplateEntry
    {
        [Key]
        public string Template { get; set; }
        public string Username { get; set; }
        public string Json { get; set; }


        public TemplateEntry()
        {
        }

        public TemplateEntry(string template, string username, string json)
        {
            Template = template;
            Username = username;
            Json = json;
        }
    }
}
