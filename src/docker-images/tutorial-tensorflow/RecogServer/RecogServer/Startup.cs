using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using WebUI.Models;
using WebUI.Utils;
using Utils.Json;
using Utils.Database;
using Newtonsoft.Json.Linq;
using System.IO;
using App.Metrics.Configuration;
using App.Metrics.Reporting.Interfaces;
using App.Metrics.Extensions.Reporting.InfluxDB;
using App.Metrics.Extensions.Reporting.InfluxDB.Client;
using Microsoft.AspNetCore.Mvc;

namespace RecogServer
{
    public class Startup
    {
        public Startup(IConfiguration configuration)
        {
            Configuration = configuration;
        }

        public IConfiguration Configuration { get; }

        // This method gets called by the runtime. Use this method to add services to the container.
        public void ConfigureServices(IServiceCollection services)
        {

            // Register no-op EmailSender used by account confirmation and password reset during development
            // For more information on how to enable account confirmation and password reset please visit https://go.microsoft.com/fwlink/?LinkID=532713

            // Configure AppMetrics. see:https://al-hardy.blog/2017/04/28/asp-net-core-monitoring-with-influxdb-grafana/
            DbConfig.Set();

            var serviceBuilder = services.AddMetrics(options =>
            {
                options.WithGlobalTags((globalTags, info) =>
                {
                    globalTags.Add("app", info.EntryAssemblyName);
                    globalTags.Add("env", "stage");
                });
            })
            .AddHealthChecks()
            .AddJsonSerialization();

            var dbName = JsonUtils.GetString("Dashboards.influxDB.dbName", DbConfig.Config);
            var dbServer = JsonUtils.GetString("Dashboards.influxDB.servers", DbConfig.Config);
            var dbPort = JsonUtils.GetType<int>("Dashboards.influxDB.port", DbConfig.Config, 0);

            if (!String.IsNullOrEmpty(dbName) && !String.IsNullOrEmpty(dbServer))
            {
                serviceBuilder.AddReporting(
                factory =>
                {
                    var dbUriString = $"http://{dbServer}";
                    if (dbPort != 0)
                        dbUriString += ":" + dbPort.ToString();
                    var dbUri = new Uri(dbUriString);
                    factory.AddInfluxDb(
                        new InfluxDBReporterSettings
                        {
                            InfluxDbSettings = new InfluxDBSettings(dbName, dbUri),
                            ReportInterval = TimeSpan.FromSeconds(5)
                        });
                });
            };

            serviceBuilder.AddMetricsMiddleware(options => options.IgnoredHttpStatusCodes = new[] { 404 });

            services.AddMvc(options => options.AddMetricsResourceFilter());
        }

        // This method gets called by the runtime. Use this method to configure the HTTP request pipeline.
        public void Configure(IApplicationBuilder app, IHostingEnvironment env, ILoggerFactory loggerFactory, IApplicationLifetime lifetime)
        {
            var loggingSec = Configuration.GetSection("Logging");
            loggerFactory.AddConsole(loggingSec);
            loggerFactory.AddDebug();
            loggerFactory.AddFile("/var/log/webui/recogserver-{Date}.log");
            var logger = loggerFactory.CreateLogger("StartUp");
            // AfterAuthentication.Register((cntroller, email) => logger.LogInformation($"...User {email} login...."));
            var loggerTimer = loggerFactory.CreateLogger("Timer");

            if (env.IsDevelopment())
            {
                app.UseDeveloperExceptionPage();
                app.UseBrowserLink();
                app.UseDatabaseErrorPage();
            }
            else
            {
                app.UseExceptionHandler("/Error");
            }

            app.UseStaticFiles();

            // AppMetrics
            app.UseMetrics();
            app.UseMetricsReporting(lifetime);

            app.UseMvc(routes =>
            {
                routes.MapRoute(
                    name: "default",
                    template: "{controller}/{action=Index}/{id?}");
            });

        }
    }
}

